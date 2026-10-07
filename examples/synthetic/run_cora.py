# -*- coding: utf-8 -*-
"""合成示范：栏3 CORA（结果合取 M ∧ Y）。

CORA 只支持清晰集与多值集，输入为 data_crisp.csv（prepare.py 以 P50 为切点二值化）。

产出：output/cora_implicants.csv（三档阈值全部质蕴涵项）
      output/cora_counts.csv（阈值—质蕴涵项数—多输出质蕴涵项数）

运行：python run_cora.py（须先跑 make_data.py、prepare.py）
"""
import importlib.metadata as metadata
import os
import sys

import cora
import numpy as np
import pandas as pd

INPUTS = ["P1_fiscal", "P2_talent", "P3_digital", "P4_cluster", "P5_openness"]
OUTS = ["M_collab", "Y_perf"]
RES = "output"
os.makedirs(RES, exist_ok=True)

try:
    _v = metadata.version("cora")
except Exception:
    _v = getattr(cora, "__version__", "?")
print("cora", _v, "| python", sys.version.split()[0], "| pandas", pd.__version__)

d = pd.read_csv("data_crisp.csv")
d["dh"] = ((d.M_collab == 1) & (d.Y_perf == 1)).astype(int)
print("N = %d   双高 M∧Y = %d (%.1f%%)" % (len(d), d.dh.sum(), 100 * d.dh.mean()))


def mask(raw):
    """把质蕴涵项的原始取值（0/1 或缺省）转成样本掩码。"""
    m = np.ones(len(d), bool)
    for v, c in zip(raw, INPUTS):
        s = set(v)
        if s == {0, 1}:
            continue
        m &= (d[c] == (1 if s == {1} else 0)).values
    return m


rows, counts = [], []
for inc in [0.70, 0.75, 0.80]:
    ctx = cora.OptimizationContext(d, output_labels=OUTS, input_labels=INPUTS, inc_score1=inc)
    imps = ctx.get_prime_implicants()
    dual = [p for p in imps if len(set(p.outputs)) == 2]
    print("-- inc=%.2f  质蕴涵项 %d 个，多输出 %d 个" % (inc, len(imps), len(dual)))
    counts.append({"阈值inc": inc, "质蕴涵项数": len(imps), "多输出质蕴涵项数": len(dual)})
    for p in imps:
        m = mask(p.raw_implicant)
        outs = sorted(p.outputs)
        rows.append({
            "阈值inc": inc,
            "质蕴涵项": str(p.implicant),
            "覆盖输出": ", ".join(OUTS[o - 1] for o in outs),
            "是否多输出": int(len(outs) == 2),
            "案例数": int(m.sum()),
            "组态内双高数": int((m & (d.dh == 1)).sum()),
            "组态内双高比例%": round(100 * d.loc[m, "dh"].mean(), 1),
            "con(M)": round((d.loc[m, "M_collab"] == 1).mean(), 3),
            "con(Y)": round((d.loc[m, "Y_perf"] == 1).mean(), 3),
        })
        print("   %-40s out=%s n=%4d 双高=%3d(%.1f%%) con[M]=%.3f con[Y]=%.3f" % (
            str(p.implicant), outs, m.sum(), int((m & (d.dh == 1)).sum()),
            100 * d.loc[m, "dh"].mean(),
            (d.loc[m, "M_collab"] == 1).mean(), (d.loc[m, "Y_perf"] == 1).mean()))

pd.DataFrame(rows).to_csv(os.path.join(RES, "cora_implicants.csv"),
                          index=False, encoding="utf-8-sig")
pd.DataFrame(counts).to_csv(os.path.join(RES, "cora_counts.csv"),
                            index=False, encoding="utf-8-sig")
print("[已落盘] output/cora_implicants.csv、output/cora_counts.csv")
