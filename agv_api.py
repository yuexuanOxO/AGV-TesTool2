import socket, struct, json, os,time
import Smap_Analysis

#port
STATUS_PORT  = 19204
TASK_STATUS_PORT    = 19204
CONFIG_PORT = 19207
TASK_PORT = 19206

#timeout
STATUS_TIMEOUT = 0.5     # 搜尋 AGV 用
MAP_TIMEOUT = 10         # 下載地圖用
CONNECT_TIMEOUT = 5


MSGTYPE_INFO = 1000       # robot_status_info_req
MSGTYPE_DOWNLOADMAP = 0x0FAB  # robot_config_downloadmap_req
MSGTYPE_NAV_STATUS = 0x03FC   # 1020
MSGTYPE_TASK_STATUS = 0x0456  # 1110
MSGTYPE_GOTARGET = 0x0BEB  # 3051 robot_task_gotarget_req
MSGTYPE_MAP_REQ = 0x0514  # robot_status_map_req 查询机器人载入的地图以及储存的地图



from concurrent.futures import ThreadPoolExecutor, as_completed

CACHE_DIR = "maps_cache"
os.makedirs(CACHE_DIR, exist_ok=True)


# === 封包處理 ===
def _pack_header(seq: int, msg_type: int, body_bytes: bytes) -> bytes:
    return struct.pack(
        ">BBH I H 6s",
        0x5A, 0x01, seq, len(body_bytes), msg_type, b"\x00"*6
    ) + body_bytes


def _read_frame(sock: socket.socket):
    # 先收 header (16 bytes)
    header = sock.recv(16)
    if len(header) < 16:
        raise Exception("回應 header 不完整")

    magic, version, seq, json_len, msg_type, _ = struct.unpack(">BBH I H 6s", header)

    # 再收 json_len bytes
    body = b""
    while len(body) < json_len:
        chunk = sock.recv(json_len - len(body))
        if not chunk:
            break
        body += chunk
    return magic, msg_type, body


def _send_recv(ip: str, port: int, msg_type: int, body: dict | None = None, timeout=CONNECT_TIMEOUT):
    body_bytes = b""
    if body is not None:
        body_bytes = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect((ip, port))
        s.sendall(_pack_header(1, msg_type, body_bytes))
        _, _, resp = _read_frame(s)

    return json.loads(resp.decode("utf-8") or "{}")


# === API 類別 ===
class Api:
    def get_robot_info(self, ip: str):
        try:
            resp = _send_recv(ip, STATUS_PORT, MSGTYPE_INFO, timeout=STATUS_TIMEOUT)
            return {"ok": True, "resp": resp}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # 掃描區網內的 AGV
    def scan_network(self, subnet: str, max_workers: int = 100):
        ips = [f"{subnet}.{i}" for i in range(1, 255)]
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ip = {executor.submit(self.get_robot_info, ip): ip for ip in ips}

            for future in as_completed(future_to_ip):
                ip = future_to_ip[future]
                try:
                    res = future.result()
                    if res.get("ok"):
                        results.append({
                            "ip": ip,
                            "vehicle_id": res["resp"].get("vehicle_id", "未知ID"),
                            "model": res["resp"].get("model", "未知型號"),
                            "map": res["resp"].get("current_map", "未知地圖"),
                            "map_md5": (res["resp"].get("current_map_entries") or [{}])[0].get("md5", "")
                        })
                except Exception:
                    pass
        return results

    # 下載地圖
    def download_map(self, ip: str, map_name: str = "default"):
        try:
            resp = _send_recv(ip, CONFIG_PORT, MSGTYPE_DOWNLOADMAP,
                              {"map_name": map_name}, timeout=MAP_TIMEOUT)
            return {"ok": True, "map": resp}
        except Exception as e:
            return {"ok": False, "error": f"下載地圖失敗：{e}"}

    # 帶有 md5 判斷與快取的 get_bins
    def get_bins(self, ip: str, map_name: str = "default", md5: str = "", force_refresh: bool = False):
        """帶有 md5 判斷與快取的 get_bins"""
        cache_json = os.path.join(CACHE_DIR, f"{map_name}.json")
        cache_md5 = os.path.join(CACHE_DIR, f"{map_name}.md5")

        smap = None

        # 先檢查快取
        if not force_refresh and os.path.exists(cache_json) and os.path.exists(cache_md5):
            try:
                with open(cache_md5, "r", encoding="utf-8") as f:
                    cached_md5 = f.read().strip()
                if md5 and cached_md5 == md5:
                    with open(cache_json, "r", encoding="utf-8") as f:
                        smap = json.load(f)
            except Exception:
                pass

        # 沒有快取或 md5 不符 → 下載
        if smap is None:
            res = self.download_map(ip, map_name)
            if not res.get("ok"):
                return res
            smap = res["map"]

            # 更新快取
            try:
                with open(cache_json, "w", encoding="utf-8") as f:
                    json.dump(smap, f, ensure_ascii=False, indent=2)
                if md5:
                    with open(cache_md5, "w", encoding="utf-8") as f:
                        f.write(md5)
            except Exception:
                pass

            source = "download"
        else:
            source = "cache"

        # === 這裡同時回傳 bins + stations + points ===
        bins = Smap_Analysis.parse_bins_actions(smap)
        points = Smap_Analysis.parse_points(smap)

        return {
            "ok": True,
            "bins": bins,
            "stations": list(points.keys()),  # ✅ 所有站點名稱 (AP/LM/PP/CP)
            "points": points,                 # ✅ 詳細資訊 (class, x, y)
            "source": source
        }

    
    #獲取機器人導航狀態
    def get_nav_status(self, ip: str, simple: bool = True):
        try:
            body = {"simple": True} if simple else {}
            resp = _send_recv(ip, TASK_STATUS_PORT, MSGTYPE_NAV_STATUS, body, timeout=1)
            return {"ok": True, "resp": resp}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    #獲取任務狀態
    def get_task_status(self, ip: str, task_ids: list[str] | None = None):
        try:
            body = {"task_ids": task_ids} if task_ids else {}
            resp = _send_recv(ip, TASK_STATUS_PORT, MSGTYPE_TASK_STATUS, body, timeout=1)
            return {"ok": True, "resp": resp}
        except Exception as e:
            return {"ok": False, "error": str(e)}
        

    #下發任務
    def dispatch_task(self, ip: str, bin_name: str, action: str, source_id: str = "SELF_POSITION"):
        if not ip:
            return {"ok": False, "error": "缺少 IP"}
        if not bin_name:
            return {"ok": False, "error": "缺少 bin_name"}

        try:
            task_id = f"t{int(time.time() * 1000)}"
            body = {
                "source_id": source_id,
                "id": bin_name,
                "binTask": action   # ✅ 保留 binTask
            }

            print("下發任務:", body)
            resp = _send_recv(ip, TASK_PORT, MSGTYPE_GOTARGET, body, timeout=3)
            return {"ok": True, "resp": resp, "task_id": task_id}
        except Exception as e:
            return {"ok": False, "error": str(e)}
        


    #獲取地圖md5
    '''
    def get_map_md5(self, ip: str, map_name: str):
        try:
            body = {"map_names": [map_name]}
            resp = _send_recv(ip, STATUS_PORT, 0x0516, body, CONNECT_TIMEOUT)
            return {"ok": True, "resp": resp}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    '''
        

    def get_current_map(self, ip: str):
        """
        查詢當前載入的地圖與 md5
        """
        if not ip:
            return {"ok": False, "error": "缺少 IP"}
        try:
            resp = _send_recv(ip, STATUS_PORT, MSGTYPE_MAP_REQ, {}, CONNECT_TIMEOUT)
            return {"ok": True, "resp": resp}
        except Exception as e:
            return {"ok": False, "error": str(e)}
