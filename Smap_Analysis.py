import json
from collections import defaultdict

# ---------- 解析庫位與動作 ----------
def parse_bins_actions(smap):
    """
    回傳結構: { pointName: { binName: [動作key, ...], ... }, ... }
    例如: { "AP12": { "Loc-3-1": ["load","unload","2F_load"] } }
    """
    bins = defaultdict(dict)
    for group in smap.get("binLocationsList", []) or []:
        for loc in group.get("binLocationList", []) or []:
            point = loc.get("pointName")
            if not point:
                continue
            bin_name = loc.get("binName") or loc.get("instanceName")
            actions = []
            for prop in loc.get("property", []):
                if prop.get("key") == "binTask":
                    s = prop.get("stringValue") or prop.get("value")
                    if not s:
                        continue
                    try:
                        tasks = json.loads(s)
                        # tasks 是一個 list，每個元素是一個 {動作key: {...}}
                        for task in tasks:
                            if isinstance(task, dict):
                                for k in task.keys():
                                    if k not in actions:
                                        actions.append(k)
                    except Exception:
                        pass
            if bin_name:
                bins[point][bin_name] = actions
    return bins


# ---------- 建立庫位對應 AP ----------
def build_bin_to_ap_map(smap):
    """
    建立 {庫位名稱: 綁定AP} 對應表
    例如: { "Loc-2-1": "AP9" }
    """
    bin_to_ap = {}
    for group in smap.get("binLocationsList", []) or []:
        for loc in group.get("binLocationList", []) or []:
            bin_name = loc.get("instanceName") or loc.get("binName")
            ap_point = loc.get("pointName")
            if bin_name and ap_point:
                bin_to_ap[bin_name] = ap_point
    return bin_to_ap


# ---------- 解析 AP 的前置點 ----------
def parse_prepoints(smap):
    """
    回傳結構: { "AP站點": "LM前置點", ... }
    例如: { "AP9": "LM10" }
    """
    prepoints = {}
    for p in smap.get("advancedPointList", []) or []:
        name = p.get("instanceName")
        if not name or not name.startswith("AP"):
            continue
        for prop in p.get("property", []):
            if prop.get("key") == "prepoint":
                val = prop.get("stringValue") or prop.get("value")
                if val:
                    prepoints[name] = val
    return prepoints


def parse_points(smap):
    """
    回傳所有站點資訊 dict
    格式: { "LM6": {"class": "LocationMark", "x": 9.294, "y": -7.954}, ... }
    """
    points = {}
    for p in smap.get("advancedPointList", []):
        name = p.get("instanceName")
        pos = p.get("pos", {})
        if name and "x" in pos and "y" in pos:
            points[name] = {
                "class": p.get("className", ""),
                "x": float(pos["x"]),
                "y": float(pos["y"]),
            }
    return points



# ---------- 測試用 ----------
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python Smap_Analysis.py <地圖.json>")
        sys.exit(1)

    path = sys.argv[1]
    with open(path, "r", encoding="utf-8") as f:
        smap = json.load(f)

    bins_actions = parse_bins_actions(smap)
    bin_to_ap = build_bin_to_ap_map(smap)
    prepoints = parse_prepoints(smap)

    for point, bin_dict in bins_actions.items():
        print(f"站點 {point}:")
        for bin_name, actions in bin_dict.items():
            print(f"  庫位 {bin_name} ： 動作 {actions}")

    print("\n=== 前置點分析 ===")
    for ap, lm in prepoints.items():
        print(f"{ap} 的前置點是 {lm}")
