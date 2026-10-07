# -*- coding: utf-8 -*-
"""生成一套**完全合成**的数据，供 worked-example 使用。

设定（虚构，不对应任何真实研究）：区域创新政策组合 → 协同创新 → 经济绩效。

- 前因：P1 财政科技投入强度、P2 人才政策覆盖度、P3 数字基础设施（0–30 整数分）、
        P4 产业集聚度、P5 对外开放度
- 中间结果：M 协同创新指数
- 末端结果：Y 经济绩效指数

真值生成过程（DGP）用模糊逻辑写成，便于对照「数据里真实存在什么结构」与
「三种方法各自识别出了什么」：

    M* = (P1 ∧ P3) ∨ (P2 ∧ P4)
    Y* = (M* ∧ P1) ∨ (P3 ∧ P5) ∨ (P2 ∧ P4)

即：协同创新有两条路径；经济绩效既有经由协同创新的链式路径，也有不经由它的直接路径
（P3∧P5 这一支），还共享 P2∧P4 这一共同原因。因此三种方法应当分别识别出：
fsQCA 的两条充分路径、CNA 的链式结构＋直接路径、CORA 的同时覆盖 M 与 Y 的多输出质蕴涵项。

运行：python make_data.py     -> data_synthetic_raw.csv
"""
import numpy as np
import pandas as pd

SEED = 20261007
N = 600

rng = np.random.default_rng(SEED)

# ── 前因（原始尺度）──────────────────────────────────────────────────────
P1 = np.clip(rng.normal(0.50, 0.20, N), 0.02, 0.99) * 10          # %（0–10）
P2 = np.clip(rng.normal(0.50, 0.24, N), 0.02, 0.99) * 100         # 覆盖度（0–100）
P3 = rng.integers(0, 31, N).astype(float)                          # 整数分（0–30），故 P50 处会有并列
P4 = np.clip(rng.normal(0.50, 0.19, N), 0.02, 0.99) * 5           # 指数（0–5）
P5 = np.clip(rng.normal(0.50, 0.23, N), 0.02, 0.99) * 100         # 指数（0–100）


def fz(x, lo, hi):
    """把原始值线性映到 [0,1] 后过 logistic，得到模糊隶属度（仅用于造数据）。"""
    z = (x - lo) / (hi - lo)
    return 1.0 / (1.0 + np.exp(-(z - 0.5) * 12.0))


a1, a2 = fz(P1, 0, 10), fz(P2, 0, 100)
a3, a4 = fz(P3, 0, 30), fz(P4, 0, 5)
a5 = fz(P5, 0, 100)

AND = lambda x, y: x * y
OR = lambda x, y: x + y - x * y

M_star = OR(AND(a1, a3), AND(a2, a4))
Y_star = OR(OR(AND(M_star, a1), AND(a3, a5)), AND(a2, a4))

# 加噪：外生冲击使个体偏离真值，这正是三种方法都要面对的经验情形
M = np.clip(M_star + rng.normal(0, 0.10, N), 0.01, 0.99)
Y = np.clip(Y_star + rng.normal(0, 0.10, N), 0.01, 0.99)

df = pd.DataFrame({
    "unit_id": ["R%03d" % (i + 1) for i in range(N)],
    "P1_fiscal": np.round(P1, 3),        # 财政科技投入强度（%）
    "P2_talent": np.round(P2, 3),        # 人才政策覆盖度（0–100）
    "P3_digital": P3,                    # 数字基础设施（0–30 整数分）
    "P4_cluster": np.round(P4, 3),       # 产业集聚度（0–5）
    "P5_openness": np.round(P5, 3),      # 对外开放度（0–100）
    "M_collab": np.round(M * 40, 3),     # 协同创新指数（0–40）
    "Y_perf": np.round(Y * 100, 3),      # 经济绩效指数（0–100）
})
df.to_csv("data_synthetic_raw.csv", index=False, encoding="utf-8")
print("已生成 data_synthetic_raw.csv  n =", len(df))
print(df.describe().round(3).to_string())
