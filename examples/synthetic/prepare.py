# -*- coding: utf-8 -*-
"""校准：原始值 -> 模糊集隶属度（Ragin 直接校准，P5/P50/P95 三锚点，端点截断 0.05/0.95）。

产出：
  data_fuzzy.csv    —— 七个变量的模糊隶属度（QCA / CNA 用）
  data_crisp.csv    —— 以 0.5 为切点二值化（CORA 用；恰为 0.5 者归入高状态）
  output/desc_stats.csv —— 描述统计 + 各变量「隶属度恰为 0.5」的案例数 + 清晰集高组占比

运行：python prepare.py（须先跑 make_data.py）
"""
import os
import numpy as np
import pandas as pd

RAW = "data_synthetic_raw.csv"
VARS = ["P1_fiscal", "P2_talent", "P3_digital", "P4_cluster", "P5_openness", "M_collab", "Y_perf"]
os.makedirs("output", exist_ok=True)

d = pd.read_csv(RAW, encoding="utf-8")
assert d[VARS].notna().all().all(), "合成数据不应有缺失值"


def cal(x, q=(5, 50, 95)):
    """Ragin 直接校准法：P5/P50/P95 三锚点，分段线性，端点截断到 0.05/0.95。"""
    a = np.percentile(x, q)
    y = np.full(len(x), np.nan)
    lo, hi = x <= a[1], x > a[1]
    y[lo] = 0.05 + 0.45 * (x[lo] - a[0]) / (a[1] - a[0])
    y[hi] = 0.50 + 0.45 * (x[hi] - a[1]) / (a[2] - a[1])
    return np.clip(y, 0.05, 0.95)


fz = pd.DataFrame({"unit_id": d["unit_id"]})
cr = pd.DataFrame({"unit_id": d["unit_id"]})
rows = []
for c in VARS:
    v = d[c].values
    fz[c] = np.round(cal(v), 6)
    cr[c] = (fz[c].values >= 0.5).astype(int)          # 恰为 0.5 者归入高状态
    a = np.percentile(v, (5, 50, 95))
    rows.append({
        "变量": c, "Mean": round(v.mean(), 3), "SD": round(v.std(ddof=1), 3),
        "Min": round(v.min(), 3), "Max": round(v.max(), 3),
        "P5": round(a[0], 3), "P50": round(a[1], 3), "P95": round(a[2], 3),
        "隶属度=0.5": int((np.abs(fz[c].values - 0.5) < 1e-9).sum()),
        "清晰集高组占比%": round(100 * cr[c].mean(), 1),
    })

fz.to_csv("data_fuzzy.csv", index=False, encoding="utf-8")
cr.to_csv("data_crisp.csv", index=False, encoding="utf-8")
pd.DataFrame(rows).to_csv("output/desc_stats.csv", index=False, encoding="utf-8-sig")

print("n =", len(fz))
print(pd.DataFrame(rows).to_string(index=False))
print("\n双高 M∧Y = %d (%.1f%%)" % (
    ((cr.M_collab == 1) & (cr.Y_perf == 1)).sum(),
    100 * ((cr.M_collab == 1) & (cr.Y_perf == 1)).mean()))
print("[已落盘] data_fuzzy.csv、data_crisp.csv、output/desc_stats.csv")
