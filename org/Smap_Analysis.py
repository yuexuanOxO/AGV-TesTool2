import json
from collections import defaultdict

# ---------- 讀取地圖 ----------
def load_smap(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ---------- 站點 ----------
def parse_points(smap):
    points = {}
    for p in smap.get("advancedPointList", []):
        name = p.get("instanceName")
        pos  = p.get("pos", {})
        if name and "x" in pos and "y" in pos:
            points[name] = {
                "class": p.get("className", ""),
                "x": float(pos["x"]),
                "y": float(pos["y"]),
            }
    return points



# ---------- 解析庫位 ----------
def parse_bins(smap):
    bins = defaultdict(list)
    for group in smap.get("binLocationsList", []):
        for loc in group.get("binLocationList", []):
            point = loc.get("pointName")
            if not point:
                continue
            for prop in loc.get("property", []):
                if prop.get("key") == "binTask":
                    s = prop.get("stringValue") or prop.get("value")
                    if not s:
                        continue
                    try:
                        tasks = json.loads(s)
                        bins[point].append(tasks)
                    except Exception:
                        pass
    return bins


# ---------- 解析庫位動作 ----------
def parse_bins_actions(smap):
    """
    回傳結構: { pointName: { binName: [動作key, ...], ... }, ... }
    例如: { "AP12": { "Loc-3-1": ["load","unload"] } }
    """
    bins = defaultdict(dict)
    for group in smap.get("binLocationsList", []):
        for loc in group.get("binLocationList", []):
            point = loc.get("pointName")
            if not point:
                continue
            bin_name = loc.get("binName") or loc.get("instanceName")
            for prop in loc.get("property", []):
                if prop.get("key") == "binTask":
                    s = prop.get("stringValue") or prop.get("value")
                    if not s:
                        continue
                    try:
                        tasks = json.loads(s)
                        # tasks 可能是一個 list，每個元素是一個 {動作key: {...}}
                        actions = []
                        for task in tasks:
                            if isinstance(task, dict):
                                for k in task.keys():
                                    if k not in actions:
                                        actions.append(k)
                        bins[point][bin_name] = actions
                    except Exception:
                        pass
    return bins


# ---------- 解析前置點 ----------
def parse_prepoints(smap):
    """
    回傳結構: { "AP站點": "LM前置點", ... }
    例如: { "AP9": "LM10" }
    """
    prepoints = {}
    for p in smap.get("advancedPointList", []):
        name = p.get("instanceName")
        if not name or not name.startswith("AP"):
            continue
        for prop in p.get("property", []):
            if prop.get("key") == "prepoint":
                val = prop.get("stringValue") or prop.get("value")
                if val:
                    prepoints[name] = val
    return prepoints



# ---------- 主程式 ----------
if __name__ == "__main__":
    smap = load_smap("AGV_map2.txt")  # 你的檔案
    #points = parse_points(smap)
    bins   = parse_bins(smap)
    bins_actions = parse_bins_actions(smap)

    # 列出所有庫位&動作
    for point, bin_dict in bins_actions.items():
        print(f"站點 {point}:")
        for bin_name, actions in bin_dict.items():
            print(f"  庫位 {bin_name} → 動作 {actions}")
            

    prepoints = parse_prepoints(smap)

    # 列出所有 AP 的前置點
    print("\n=== 前置點分析 ===")
    for ap, lm in prepoints.items():
        print(f"{ap} 的前置點是 {lm}")

    print(prepoints.get("AP9"))   # 輸出 "LM10"
            