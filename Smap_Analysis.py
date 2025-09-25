# Smap_Analysis.py
import json
from collections import defaultdict

def _extract_actions_from_props(props):
    """從 property 陣列裡的 binTask 解析出動作鍵名列表"""
    if not props:
        return []
    s = ""
    for p in props:
        if p.get("key") == "binTask":
            s = p.get("string_value") or p.get("value") or ""
            break
    if not s:
        return []
    try:
        tasks = json.loads(s)
    except Exception:
        return []
    actions = []
    for t in tasks:
        if isinstance(t, dict):
            for k in t.keys():
                if k not in actions:
                    actions.append(k)
    return actions

def parse_bins_actions(smap):
    bins = defaultdict(dict)

    # 1) 舊格式：binLocationsList -> binLocationList
    for group in smap.get("binLocationsList", []) or []:
        for loc in group.get("binLocationList", []) or []:
            point = loc.get("pointName")
            if not point:
                continue
            bin_name = loc.get("binName") or loc.get("instanceName")
            actions = _extract_actions_from_props(loc.get("property"))
            if bin_name:
                bins[point][bin_name] = actions

    # 2) 新格式：stations -> { point: { bin_locations: [...] } }
    stations = smap.get("stations") or {}
    for point, info in stations.items():
        for loc in (info.get("bin_locations") or []):
            bin_name = loc.get("instance_name") or loc.get("binName")
            point_name = loc.get("point_name") or point
            actions = _extract_actions_from_props(loc.get("property"))
            if bin_name:
                bins[point_name][bin_name] = actions

    return bins
