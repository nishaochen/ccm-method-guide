# ccm-method-guide

**组态比较方法（CCM）的方法选型指南 —— 以「结果关系结构」为第一性判据。**

一个 Claude Code / Claude Agent Skill：拿到研究问题后，先判断它指向的是哪一种**结果关系结构**，
再结合研究目的与数据条件，决定用 **QCA**、**CNA**、**CORA** 还是叠加 **NCA**，并给出参数默认值
与必须一并报告的边界。

> 核心立场：**「该用 QCA 还是 CNA/CORA」这个问题不该由方法优劣回答，而应由研究问题的结果关系结构回答。**
> 结果结构划定方法的**逻辑胜任边界**（能不能表达），样本量、数据形态、时间信息划定**经验适用边界**
> （能不能稳定识别）。顺序不能反。

---

## 它解决什么问题

| 你会问的问题 | 本 skill 怎么答 |
| --- | --- |
| 我该用 QCA 还是 CNA／CORA？ | 先问「几个结果、结果之间是什么关系」，再匹配方法 |
| 已经跑了回归，还要不要再加 fsQCA？ | 先做「前置判断」：净效应问题不属 CCM 家族，不必硬套 |
| 我有多个结果，怎么建模？ | 分五类结构判定：独立 / 合取 / 因果链 / 共同原因 |
| 两个结果要同时实现怎么办？ | 判为 R3 结果合取 → CORA，并检查数据形态约束 |
| QCA 能不能做中介或因果链？ | 判为 R4 因果链，再按研究目的分流为「理论检验」或「结构发现」 |
| 一因多果 / multifinality 怎么处理？ | 从结果侧复杂性切入的五类结构分类 |
| 我的设计有什么坑？ | 设计检查清单：时间口径、结果同年、条件数、测度分层、0.5 边界案例…… |

## 五类结果关系结构

| 编号 | 结构 | 被解释对象 | 方法 |
| --- | --- | --- | --- |
| R1 | 单一结果 | `Y` | QCA / fsQCA |
| R2 | 独立多结果 | 彼此独立、分别建模的 `Y1`、`Y2` | 分别做 QCA |
| R3 | 结果合取 | `Y1 ∧ Y2` | **CORA** |
| R4 | 因果链 | `X → M → Y`（M 既是果又是因） | **CNA**，或按研究目的分流 |
| R5 | 共同原因 | 同一条件同时驱动 `Y1`、`Y2` | **CNA** |

R4 之下再按研究目的分流：**理论检验**（已明确提出机制、要分阶段检验净效应）→ 复杂中介模型 / 两阶段 QCA；
**结构发现**（只给定大致层级，要由数据识别具体结构）→ CNA。

## 安装

作为 Claude Code 的用户级 skill 安装：

```bash
git clone https://github.com/<your-name>/ccm-method-guide.git ~/.claude/skills/ccm-method-guide
```

装好后，在对话里提到「多个结果怎么建模」「方法选型」「结果合取」「QCA 还是 CNA」等问题时会自动触发；
也可以显式调用：

```
/ccm-method-guide
```

## 用法

### 直接问

把研究问题、变量清单与数据条件讲清楚，skill 会按统一模板输出：

```
【推荐方法】【结构判定】【理由】【默认数据形态】
【关键参数】【必须先解决的设计问题】【必须一并报告的边界】
```

### 命令行脚本

不依赖 Claude 也能用选型脚本：

```bash
python scripts/select_method.py                 # 交互问答（前置一问 + 五步）
python scripts/select_method.py --question net-effect

python scripts/select_method.py --outcomes 2 --relation conjunctive \
    --cases 600 --conditions 5 --data fuzzy --outcome-names "M,Y"

python scripts/select_method.py --outcomes 2 --relation chain --goal discover --json
```

## 仓库结构

```
SKILL.md                     skill 主文件（五步选型流程 + 输出模板 + 硬性提醒）
references/
  structures.md              五类结构的判定问句、边界情形与常见误判清单
  method-specs.md            四法对照 + 各方法参数默认值、代码片段、报告项
  design-checklist.md        设计 / 校准 / 稳健性 / 报告逐项检查清单
  worked-example.md          同一批合成数据的三种结构示范（fsQCA / CNA / CORA 全文写法）
scripts/
  select_method.py           命令行选型助手（含 --json）
examples/synthetic/          示范用的合成数据与四段分析脚本，一条命令可复跑
evals/evals.json             提示集（用于检验 skill 的触发与输出质量）
```

## 示范：同一批数据，三种结果结构

`references/worked-example.md` 用一套**完全合成**的区域创新数据（n = 600，随机种子固定）演示：

- 数据生成过程写成模糊逻辑，**真实结构是已知的**，因此可以对照「数据里本来有什么」与「三种方法各自识别出了什么」；
- 同一份数据、同一套校准，只改变被解释对象：
  R1 单一结果 → fsQCA；R4 因果链 → fuzzy CNA；R3 结果合取 → CORA；
- 三个脚本一键复跑，文中每个数字都能自己算出来：

```bash
cd examples/synthetic
python run_all.py     # 造数 -> 校准 -> fsQCA/CNA -> CORA
```

（QCA/CNA 需 R 环境；CORA 需 Python + `cora` 包，可用 `RSCRIPT` 与 `CORA_PYTHON` 环境变量分别指定。）

## 依赖

- **本 skill 的核心（SKILL.md、references、select_method.py）零依赖**，纯文本 + 标准库 Python。
- `examples/synthetic/` 才需要：R ≥ 4.2 且装有 `QCA`、`cna`；Python ≥ 3.9 且装有 `cora`、`pandas`、`numpy`。

## 边界与免责

- 本 skill 给出的是**方法匹配与设计提示**，不替代对研究问题本身的理论判断。
- 它**不比较方法优劣**；不同方法的一致性／覆盖度口径不同（CORA 的 `con`、fsQCA 的 `inclS`、CNA 的 `con`
  不是同一统计量），数值不可直接比大小。
- 参数默认值是**起点**，必须结合你自己的数据与理论重新论证。

## 相关

`ccm-research-guide` 管「适不适合做组态研究、论文怎么写、怎么回应审稿人」；
本 skill 只管一件事——**在 CCM 家族内部怎么选方法、选完怎么设定参数**。两者可叠加使用。

## English

An Agent Skill for **method selection within the Configurational Comparative Methods (CCM) family**
(QCA / CNA / CORA / NCA). It identifies the *outcome-relationship structure* implied by a research
question — single outcome, independent multiple outcomes, outcome conjunction, causal chain, or common
cause — and then matches that structure to a method, in light of research objectives and data
conditions. It ships a five-step decision procedure, a design/reporting checklist, a CLI selector
(`scripts/select_method.py`), and a fully reproducible synthetic worked example that runs fsQCA,
fuzzy CNA, and CORA on the same data under three different outcome structures.
Primary language: Chinese.

## 许可

MIT（见 `LICENSE`）。
