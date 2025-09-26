import socket, struct, json
import Smap_Analysis #自製的解析庫位模組

STATUS_PORT = 19204
CONFIG_PORT = 19207

CONNECT_TIMEOUT = 1
MSGTYPE_INFO = 1000  # robot_status_info_req
MSGTYPE_DOWNLOADMAP = 0x0FAB   # 4011 robot_config_downloadmap_req

#搜尋網段用
from concurrent.futures import ThreadPoolExecutor, as_completed

def _send_recv(ip: str, port: int, msg_type: int, body: dict | None = None, 
               timeout: int = CONNECT_TIMEOUT, read_all: bool = False):
    body_bytes = b""
    if body:
        body_json = json.dumps(body, separators=(',', ':')).encode("utf-8")
        body_bytes = body_json

    header = struct.pack(
        ">BBH I H 6s",
        0x5A, 0x01, 1, len(body_bytes), msg_type, b"\x00"*6
    )
    packet = header + body_bytes

    with socket.create_connection((ip, port), timeout=timeout) as s:
        s.sendall(packet)

        if read_all:
            # 讀完整資料直到 socket 關閉
            chunks = []
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
            data = b"".join(chunks)
        else:
            # 只收一次就結束（適合狀態查詢）
            data = s.recv(4096)

    json_str = data.split(b"{", 1)[-1]
    json_str = b"{" + json_str
    return json.loads(json_str.decode("utf-8"))


class Api:
    def get_robot_info(self, ip: str):
        try:
            resp = _send_recv(ip, STATUS_PORT, MSGTYPE_INFO)
            return {"ok": True, "resp": resp}
        except Exception as e:
            return {"ok": False, "error": str(e)}
        

    #
    def scan_network(self, subnet: str, max_workers: int = 20):
        """
        掃描一整個網段，使用多執行緒加快速度
        """
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
                            "map": res["resp"].get("current_map", "未知地圖")
                        })
                except Exception:
                    pass
        return results


    def download_map(self, ip: str, map_name: str = "default"):
        try:
            resp = _send_recv(ip, CONFIG_PORT, MSGTYPE_DOWNLOADMAP, {"map_name": map_name}, read_all=True)
            return {"ok": True, "map": resp}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_bins(self, ip: str, map_name: str = "default"):
        res = self.download_map(ip, map_name)
        if not res.get("ok"):
            return res
        smap = res["map"]
        bins = Smap_Analysis.parse_bins_actions(smap)
        return {"ok": True, "bins": bins}