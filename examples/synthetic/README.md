# 合成示范数据：同一批数据的三种结果结构

配合 `../../references/worked-example.md`。**数据完全是合成的**，不对应任何真实研究，
随机种子固定（`20261007`），因此结果可复现、可改动、可用来做敏感性实验。

## 一键复跑

```bash
cd examples/synthetic
python run_all.py
```

解释器路径可用环境变量覆盖：

```bash
RSCRIPT="/c/Program Files/R/R-4.6.1/bin/Rscript.exe" \
CORA_PYTHON="C:/Users/me/cora_env/Scripts/python.exe" \
python run_all.py
```

- `RSCRIPT` 指向装了 `QCA`、`cna` 的 R 解释器（**`Rscript` 常不在 PATH 上，建议写全路径**）；
- `CORA_PYTHON` 指向装了 `cora` 的 Python 解释器（CORA 通常装在与主环境不同的 venv 里）。

## 分步执行

| 步骤 | 命令 | 产出 |
| --- | --- | --- |
| 1. 造数 | `python make_data.py` | `data_synthetic_raw.csv`（原始尺度） |
| 2. 校准 | `python prepare.py` | `data_fuzzy.csv`、`data_crisp.csv`、`output/desc_stats.csv` |
| 3. fsQCA + CNA | `Rscript run_analysis.R` | `output/fsqca_paths.csv`、`necessity.csv`、`cna_con0*.csv`、`cna_counts.csv` |
| 4. CORA | `python run_cora.py` | `output/cora_implicants.csv`、`cora_counts.csv` |

## 数据生成过程（真值结构是已知的）

研究情境（虚构）：区域创新政策组合 → 协同创新 → 经济绩效。

```
M* = (P1 ∧ P3) ∨ (P2 ∧ P4)
Y* = (M* ∧ P1) ∨ (P3 ∧ P5) ∨ (P2 ∧ P4)
```

再用模糊隶属度加正态扰动生成观测值，最后**用 P5/P50/P95 直接校准**回模糊集——
刻意保留「原始值 → 校准」这一步，因为它本身就是要报告的环节。

## 特意埋进去的几个点

- **`P3_digital` 是 0–30 的整数分**：样本一大就必然有案例恰好落在 P50 上（本例 15 家），
  于是可以演示「隶属度恰为 0.5 的案例」如何被处理、以及它对真值表的实际影响。
- **`M` 被前因部分决定**：`P1·P3` 在数据里已足以确定 `M` 高，
  于是 fsQCA 的简约解/中间解会把 `M` 从该条路径中消掉——
  这是「只看中间解会误判结构位置」的现成教材。
- **`P3·P5` 只覆盖 `Y` 不覆盖 `M`**：CORA 的单输出质蕴涵项会把它拎出来，
  用来演示「单一目标的实现 ≠ 多目标的同步实现」。
- **`P2·P4` 是共同原因**：在 CORA 中作为 `M` 的质蕴涵项出现，可与真值结构对照。

## 结果一览（inc/con = 0.75 档）

**fsQCA**（复杂解，6 条件 → `Y`，三档阈值同解）：

```
P1·P3·M  +  P2·P4·M  +  P3·P5·M  +  P1·P4·P5·M      总体解 0.930 / 0.864 / 0.772
```

**fuzzy CNA**（排序 `P1..P5 ＜ M ＜ Y`）：对 `M` 返回 19 项、对 `Y` 返回 10 项；
`M` 侧前两位正是 `P1·P3`（0.901）与 `P2·P4`（0.881）。

**CORA**（输入 5 前因，输出 `M` 与 `Y`）：7 个质蕴涵项，其中 **4 个同时覆盖 `M` 与 `Y`**；
单输出项 `P1·P3`、`P2·P4` 只覆盖 `M`，`P3·P5` 只覆盖 `Y`。

完整数字与读法见 `../../references/worked-example.md`。

## 版本

R 4.6.1 + QCA 3.25 + cna 4.0.3；Python 3.10.9 + cora 1.0.1 + pandas 2.3.3。
