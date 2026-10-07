#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ccm-method-guide 决策脚本。

按「结果关系结构 → 方法」的判据给出一版推荐结论：
推荐方法、结构判定、理由、默认数据形态、关键参数、先要解决的设计问题、必须报告的边界。

用法
----
交互问答（五步）：
    python select_method.py

一次性给参数：
    python select_method.py --outcomes 2 --relation conjunctive \
        --cases 600 --conditions 5 --data fuzzy --outcome-names "M,Y"

机器可读：
    python select_method.py --outcomes 2 --relation chain --goal discover --json

注意：脚本只编码了「结构 → 方法」的判据与数据条件检查，
      它**不能替代**对研究问题本身的判断。--relation 填不准时先读 references/structures.md。
"""

import argparse
import json
import sys

# Windows 控制台默认 GBK，直接 print 中文会乱码或抛 UnicodeEncodeError。
# 把标准输出/错误强制为 UTF-8，使用者不必再加 PYTHONUTF8=1。
for _s in ("stdout", "stderr"):
    _stream = getattr(sys, _s, None)
    if _stream is not None and getattr(_stream, "encoding", "").lower().replace("-", "") != "utf8":
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

# ---------------------------------------------------------------- 基础数据

RELATION_LABEL = {
    "independent": "R2 独立多结果（结果之间没有需要解释的关系）",
    "conjunctive": "R3 结果合取（多个结果必须同步实现）",
    "chain": "R4 因果链（结果之间存在先后／层级）",
    "common": "R5 共同原因（同一条件同时驱动多个结果）",
    "mixed": "多种结构并存",
}

DATA_LABEL = {
    "fuzzy": "模糊集",
    "crisp": "清晰集",
    "multivalue": "多值集",
    "continuous": "连续变量（尚未校准）",
}

# 各方法的默认参数（示例口径，须结合自己的数据与理论重新论证）
PARAMS = {
    "fsQCA": [
        "校准锚点 P5/P50/P95 直接校准，端点截断 0.95/0.05；另跑 P10/P50/P90 做敏感性",
        "频数阈值 1（大样本可提高）；PRI ≥ 0.70",
        "充分性一致性分 0.70 / 0.75 / 0.80 三档检验，报告三档解是否相同",
        "剔除结果变量隶属度恰为 0.5 的案例，并报告各变量 0.5 案例数",
        "报告中间解，并说明复杂解、简约解是否与之相同",
    ],
    "CNA": [
        "因果排序 ordering 依理论与时间逻辑设定（如「前因 ＜ 中间结果 ＜ 末端结果」）",
        "strict = TRUE（逻辑冗余自由）；suff.only = TRUE（只输出最小充分条件集合，用「→」）",
        "con = 0.75、cov ≥ 0.35 双硬门槛；并跑 0.70 / 0.80 看稳健性",
        "0.5 隶属度案例可保留（与 QCA 不同），仍应报告数量",
        "报告解的非唯一性；注意 suff.only = TRUE 下不产出 ASF/CSF",
    ],
    "CORA": [
        "仅清晰集或多值集；以 P50 为切点二值化，须显式报告切点与边界值归向",
        "inc_score 默认 0.75，并跑 0.70 / 0.80",
        "组态内比例类指标给出分子、分母与计算对象",
        "说明质蕴涵项覆盖的案例可以重叠，不构成对样本的划分",
    ],
    "分阶段方法": [
        "复杂中介模型（QCA + 回归）：先由 QCA 识别何种前因组态充分于中介变量，再交由回归估计中介与直接效应",
        "两阶段 QCA：把研究问题拆为两个阶段的 QCA，分别建模后再整合",
        "两者都是「分结果建模、事后拼接」，跨结果的结构冗余与虚假关联仍可能存在，报告时须交代",
    ],
    "NCA": [
        "对每个候选前因算天花板线，报告效应量与 p 值",
        "必要性须有理论依据；不要因某条件反复出现在充分组态中就当必要条件",
        "NCA 定位瓶颈后，再交由 fsQCA / CNA 做充分性组态分析",
    ],
}

BOUNDARIES = {
    "QCA": "不能据单一结果的路径推断跨结果结构，也不能据此确立中介地位；"
           "单结果视角是扁平的，所有条件处于同一分析层级。",
    "CNA": "链式充分结构不等同于因果效应或完整中介；排序只是搜索约束，不能排除共同前因、"
           "样本选择与测量误差；结论受排序设定与阈值选择约束。",
    "CORA": "二值化压缩了程度信息；共享组态不代表唯一实现路径；"
            "con 不可与 fsQCA 的 inclS、CNA 的 con 直接比较。",
}


# ---------------------------------------------------------------- 前置判断

def not_ccm():
    """前置判断（决策树第一问）：平均净效应问题不属 CCM，不做方法选型。"""
    return {
        "structure": "不属 CCM——这是平均净效应问题",
        "methods": ["回归 / SEM 等变量导向方法"],
        "rationale": [
            "选型决策树的第一问是「研究关注的是平均净效应，还是条件组态」。"
            "本问题是「X 平均而言让 Y 提高多少」，属平均处理效应，应由变量导向方法回答。",
            "CCM 回答的是「哪些条件组合与结果稳定对应」，与净效应是两类不同的问题，"
            "因此不存在「该用 QCA 还是 CNA／CORA」的选型问题，也不必为了方法多样性叠加 fsQCA。",
        ],
        "data_form": ["按变量导向方法的常规要求处理（不涉及校准为模糊隶属度）。"],
        "params": [],
        "design_issues": [
            "若确实要做组态分析，须先把研究问题改写成「哪些条件组合与高结果稳定对应」；"
            "那是独立的新研究问题，而不是原净效应回归的补充检验。",
        ],
        "warnings": [],
        "boundaries": [
            "CCM 的一致度／覆盖度不等于效应大小，不能据此推断净效应；"
            "反过来，回归系数也说明不了某条件组合是否为结果的充分条件。",
        ],
        "report_boundaries": [
            "若同一篇论文并列两类问题，须分别交代各自的被解释对象与推断逻辑，不能让一方为另一方作证",
        ],
    }


# ---------------------------------------------------------------- 决策逻辑

def recommend(outcomes, relation, goal, data, cases, conds, necessity,
              outcome_names=None, condition_names=None):
    """返回推荐结论字典。"""
    rec = {
        "structure": None,
        "methods": [],
        "rationale": [],
        "data_form": [],
        "params": [],
        "design_issues": [],
        "boundaries": [],
        "warnings": [],
    }
    outs = outcome_names or "Y1、Y2…"
    conds_txt = condition_names or "各前因条件"

    if outcomes == 1:
        rec["structure"] = "R1 单一结果"
        rec["methods"] = ["QCA / fsQCA"]
        rec["rationale"].append(
            "研究问题只解释一个结果，本身并不要求方法同时表达多个结果之间的关系，"
            "QCA 是直接且适宜的选择。")
        rec["rationale"].append(
            "注意：在特定参数条件下，CNA 的原子解与 QCA 的简约解可对同一单结果关系作等价表达，"
            "但存在噪声与不同阈值设定时二者会分岔。不要为了「方法新颖」把 R1 的 QCA 换成 CNA；"
            "如需交叉验证，可并跑 CNA 并报告分岔条件。")
        rec["params"] += PARAMS["fsQCA"]
        rec["boundaries"].append(BOUNDARIES["QCA"])
        if data in ("crisp", "multivalue"):
            rec["data_form"].append(
                "结果与条件均为%s：csQCA/mvQCA 可行，但若变量本质是程度而非有无，"
                "模糊集仍更能保留信息。" % DATA_LABEL[data])
            rec["design_issues"].append(
                "说明为何选择清晰集／多值集而非模糊集校准——这是审稿人常问的问题。")
        elif data == "continuous":
            rec["data_form"].append(
                "尚未校准：连续变量原则上采用模糊集校准（三锚点须有理论或经验依据），"
                "并报告敏感性检验。")
        else:
            rec["data_form"].append("模糊集（fsQCA 主流形态）。")

    elif relation == "independent":
        rec["structure"] = "R2 独立多结果"
        rec["methods"] = ["分别以各结果为对象开展 QCA"]
        rec["rationale"].append(
            "结果之间不存在理论上需要解释的关系。此时「多个结果」本身并不构成 QCA 的能力缺陷，"
            "分别建模具有充分的合理性——真正需要改变方法的是结果之间存在需要被解释的结构关系。")
        rec["params"] += PARAMS["fsQCA"]
        rec["boundaries"].append(BOUNDARIES["QCA"])
        rec["design_issues"].append(
            "「彼此独立」是**理论判断**：指研究者不打算解释其关系，而不是相关系数低。"
            "若两个结果在理论上显然相互影响，应改判为因果链或共同原因结构。")
        rec["design_issues"].append(
            "若研究重点随后转向「多个结果的共同前因」，应改用 CNA。")
        rec["data_form"].append("各结果分别按 fsQCA 的校准方案处理。")
        if data == "continuous":
            rec["data_form"].append("连续变量须先完成模糊集校准，不要直接以原始值入模。")

    elif relation == "conjunctive":
        rec["structure"] = "R3 结果合取"
        rec["methods"] = ["CORA"]
        rec["rationale"].append(
            "研究对象不是 %s 分别如何产生，而是二者的合取如何产生——"
            "「Y1·Y2」本身构成一个不可拆分的被解释对象。" % outs)
        rec["rationale"].append(
            "CNA 虽然面向多结果，但在形成原子解时逐结果做输出级最小化，"
            "共享原因中那些对单个输出看似冗余的条件会被逐一删去；这一盲区是代数层面的。"
            "CORA 用多输出质蕴涵项把「不可归约」的要求从单个结果提升到整个结果系统，"
            "是唯一能同时解释个体结果与结果合取的方法。")
        rec["params"] += PARAMS["CORA"]
        rec["boundaries"].append(BOUNDARIES["CORA"])
        rec["data_form"].append(
            "CORA 只支持清晰集与多值集。用模糊集数据时须先二值化或多值化，"
            "并显式报告切点（如 P50）与边界值归向（如恰为 0.5 者归入高状态）。")
        rec["design_issues"].append(
            "★ 必须核对：参与合取的多个结果是否取自**同一年份**。"
            "若年份不同，那实质是「先后实现」而非「同时实现」，结构已被偷换，应改判为因果链。")
        rec["design_issues"].append(
            "不要为了适应 CORA 的数据形式而把原始连续变量机械二值化——"
            "数据形态决定可行性，不决定方法选择的方向。")

    elif relation in ("chain", "common"):
        structure = "R4 因果链" if relation == "chain" else "R5 共同原因"
        rec["structure"] = structure
        if relation == "chain":
            if goal == "test":
                rec["methods"] = ["复杂中介模型 / 两阶段 QCA"]
                rec["rationale"].append(
                    "理论上已明确提出「前因—中介—结果」机制，研究目的是分阶段检验组态关系与净效应，"
                    "因此适合分阶段方法。")
                rec["params"] += PARAMS["分阶段方法"]
                rec["design_issues"].append(
                    "若后续希望由数据识别整体因果结构（而非检验预设机制），应补做 CNA——两者互补，"
                    "判断依据是「预设得够不够清楚」，不是「哪个更先进」。")
            elif goal == "discover":
                rec["methods"] = ["CNA（fuzzy CNA）"]
                rec["rationale"].append(
                    "能依据理论与时间顺序给出变量的大致层级，但希望由数据进一步识别具体因果链与共同原因，"
                    "CNA 能在同一分析框架中处理多个结果并识别结果之间的因果关联。")
                rec["params"] += PARAMS["CNA"]
            else:
                rec["methods"] = ["CNA（结构发现）", "或 复杂中介 / 两阶段 QCA（理论检验）"]
                rec["rationale"].append(
                    "因果链结构下的方法分流取决于研究目的：已明确提出中介机制、要分阶段检验 → "
                    "分阶段方法；希望由数据识别整体结构 → CNA。**请先明确研究目的**，两种路线的"
                    "数据准备与报告要求不同。")
                rec["params"] += PARAMS["分阶段方法"] + PARAMS["CNA"]
        else:
            rec["methods"] = ["CNA（fuzzy CNA）"]
            rec["rationale"].append(
                "同一条件同时驱动多个结果时，分别做 QCA 只能得到两个相互独立的解，"
                "无法直接识别该条件是连接多个结果的共同原因，两个独立解甚至可能掩盖真实的因果网络结构。"
                "CNA 的复杂解公式中，中介结果身兼二职，正是把多个结果组织成因果网的能力所在。")
            rec["params"] += PARAMS["CNA"]
        rec["boundaries"].append(BOUNDARIES["CNA"])
        rec["design_issues"].append(
            "★ 时间口径必须自洽：作条件者与其余条件同期，作结果者滞后于条件；"
            "因果链才逐层滞后。任何排序都不能排除共同前因、样本选择与测量误差。")
        if relation == "chain" and goal == "test":
            rec["data_form"].append(
                "模糊集校准（QCA 与回归均以此为输入）；须报告三锚点及依据。")
            if data == "continuous":
                rec["data_form"].append("连续变量须先完成校准，不要直接以原始值入模。")
        elif relation == "chain" and goal is None:
            rec["data_form"].append(
                "模糊集。结构发现路线（CNA）与理论检验路线（分阶段方法）都以模糊集为输入，"
                "但前者还须给出因果排序，后者须给定方向性预期。")
        elif data in ("fuzzy", "crisp", "multivalue"):
            rec["data_form"].append("CNA 支持%s，无需二值化。" % DATA_LABEL[data])
        else:
            rec["data_form"].append(
                "连续变量须先校准为模糊集（CNA 支持清晰集、多值集与模糊集）。")

    else:  # mixed
        rec["structure"] = "多种结构并存"
        rec["methods"] = ["方法组合：fsQCA 主分析 + CNA 交叉验证（+ CORA 补充复杂效应）"]
        rec["rationale"].append(
            "同一研究问题涉及多种结果结构时，应并列报告，或在理论支持下采用方法组合，"
            "而不是硬塞进一个方法。稳妥的组合是 fsQCA（单结果充分组态）+ CNA（多结果结构交叉验证）"
            "+ CORA（多结果同步实现）。")
        rec["rationale"].append(
            "两条独立算法路线（QCA 自上而下 / CNA 自下而上）得到一致结论，构成强稳健性论证；"
            "不一致则本身是有价值的方法学发现。")
        rec["params"] += PARAMS["fsQCA"] + PARAMS["CNA"] + PARAMS["CORA"]
        rec["boundaries"] += [BOUNDARIES["QCA"], BOUNDARIES["CNA"], BOUNDARIES["CORA"]]
        rec["design_issues"].append(
            "★ 三组分析的被解释对象不同，须分别交代样本口径与阈值设定，"
            "并说明差异仅来自结果关系结构。")
        rec["data_form"].append("按各方法要求分别准备数据（CORA 需清晰集或多值集）。")

    # ---------------- 必要性
    if necessity == "hypothesis":
        rec["methods"].append("（叠加）NCA")
        rec["rationale"].append(
            "研究问题中存在理论上的必要性假设，因此在充分性组态分析之外增加必要性检验。"
            "NCA 定位必要瓶颈并刻画其程度约束，再交由 QCA/CNA 做充分性组态。")
        rec["params"] += PARAMS["NCA"]
    elif necessity == "none" and outcomes > 1:
        rec["design_issues"].append(
            "尚未判断是否存在必要性假设。若某条件在理论上可能是「缺了就不行」的瓶颈，"
            "应补做必要性检验；但不要因为某条件反复出现在充分组态里就把它解释成必要条件。")

    # ---------------- 数据条件检查
    if cases and conds:
        limit = cases / 4.0
        if conds > limit:
            rec["warnings"].append(
                "条件数 %g 超过案例数的四分之一（N/4 = %.1f）。"
                "应先依据理论意义删除冗余或高度重叠的条件，"
                "不要通过机械降低一致性阈值来扩大可识别空间。" % (conds, limit))
        else:
            rec["warnings"].append(
                "数据条件检查：条件数 %g ≤ N/4 = %.1f（N = %d），通过。" % (conds, limit, cases))
        # 下限：条件太少同样做不了组态分析，而 k ≤ N/4 不会提示这一点
        if conds <= 1:
            rec["warnings"].append(
                "★ 条件数为 %g，理论真值表只有 %d 行，**没有组态可言**。"
                "请检查是否把本可拆分的多维构念整体合成了一个变量；"
                "若构念理论上不可分，组态比较方法并不适用。" % (conds, 2 ** conds))
        elif conds == 2:
            rec["warnings"].append(
                "条件数为 2，理论真值表仅 %d 行，组态分析的解释空间很有限。"
                "先确认这些条件是否还能按理论维度进一步拆分。" % (2 ** conds))
        if cases < 2 ** conds:
            rec["warnings"].append(
                "有限多样性提示：理论真值表 %d 行多于案例数 %d，经验覆盖必然稀疏，"
                "须报告实际被覆盖的行数与单案例行，并考虑精简条件。" % (2 ** conds, cases))
    elif conds or cases:
        rec["design_issues"].append(
            "请同时提供案例数与条件数，以便检查 k ≤ N/4 的操作性上限，"
            "以及理论真值表 2^k 行与案例数的关系。")

    if "CORA" in " ".join(rec["methods"]) and data == "fuzzy":
        rec["warnings"].append(
            "数据形态：CORA 不支持模糊集，须先二值化或多值化并报告切点。"
            "二值化会把程度差异压缩为两类，结论应限定在相应的清晰集口径下解释。")
    if not rec["data_form"]:
        rec["data_form"].append("按所选方法的数据形态要求准备。")

    rec["report_boundaries"] = [
        "阈值敏感性分档报告，区分「多档稳定出现」与「仅在特定阈值下成立」两类结构",
        "紧贴阈值的一致性须交代其随阈值提高而变化或消失的条件，不表述为稳定发现",
        "报告软件及版本、样本筛选口径、校准锚点、全部阈值参数，使正文数字可复现",
        "不比较方法优劣；跨方法对照以研究问题与结果结构的一致性为基础",
    ]
    return rec


# ---------------------------------------------------------------- 输出

def render(rec, data, cases, conds):
    L = []
    L.append("=" * 66)
    L.append("【推荐方法】" + " ＋ ".join(rec["methods"]))
    L.append("【结构判定】" + rec["structure"])
    L.append("=" * 66)
    L.append("")
    L.append("【理由】")
    for x in rec["rationale"]:
        L.append("  · " + x)
    L.append("")
    L.append("【默认数据形态】")
    for x in rec["data_form"]:
        L.append("  · " + x)
    L.append("")
    L.append("【关键参数】")
    for x in rec["params"]:
        L.append("  · " + x)
    if rec["design_issues"]:
        L.append("")
        L.append("【必须先解决的设计问题】")
        for x in rec["design_issues"]:
            L.append("  · " + x)
    if rec["warnings"]:
        L.append("")
        L.append("【数据条件检查】")
        for x in rec["warnings"]:
            L.append("  · " + x)
    L.append("")
    L.append("【必须一并报告的边界】")
    for x in rec["boundaries"]:
        L.append("  · " + x)
    L.append("")
    L.append("【报告清单】")
    for x in rec["report_boundaries"]:
        L.append("  · " + x)
    L.append("")
    L.append("提示：以上为按「结构 → 方法」判据得到的一版结论，不替代对研究问题本身的判断。")
    L.append("      更细的判定、边界情形与常见误判见 references/structures.md。")
    return "\n".join(L)


# ---------------------------------------------------------------- 交互

def ask(prompt, options, default=None):
    """options: [(key, label)]"""
    print()
    print(prompt)
    for i, (_k, label) in enumerate(options, 1):
        print("  %d) %s" % (i, label))
    while True:
        s = input("请选择编号%s： " % ("（回车默认 %s）" % default if default else "")).strip()
        if not s and default:
            return default
        if s.isdigit() and 1 <= int(s) <= len(options):
            return options[int(s) - 1][0]
        print("  请输入 1–%d 之间的编号。" % len(options))


def ask_int(prompt, default=None):
    while True:
        s = input(prompt).strip()
        if not s and default is not None:
            return default
        try:
            return int(s.replace(",", "").replace(" ", ""))
        except ValueError:
            print("  请输入整数（可留空跳过）。")


def interactive():
    print("=" * 66)
    print("CCM 方法选型辅助工具 · 前置一问 + 五步问答")
    print("=" * 66)
    print("回答以下问题即可得到方法推荐。若某步拿不准，先读 references/structures.md。")

    q = ask("前置判断：这项研究问的是平均净效应，还是条件组态？",
            [("configurational", "条件组态——哪些条件组合与结果稳定对应"),
             ("net-effect", "平均净效应——X 平均而言让 Y 提高多少")],
            default="configurational")
    if q == "net-effect":
        return {"_net_effect": True}

    n_out = ask("第一步：这项研究要解释的结果有几个？",
                [("1", "一个结果"), ("2", "两个结果"), ("many", "三个及以上结果")],
                default="1")

    outcomes = 1 if n_out == "1" else (2 if n_out == "2" else 3)
    relation = None
    goal = None
    if outcomes > 1:
        relation = ask("第二步：多个结果之间，有没有你**理论上需要解释**的关系？",
                       [("independent", "没有——彼此独立，不打算解释其关系"),
                        ("conjunctive", "有——它们必须同时实现"),
                        ("chain", "有——存在先后或层级（一个结果又是后续结果的原因）"),
                        ("common", "有——同一个条件同时驱动这几个结果"),
                        ("mixed", "两种以上上述关系并存")])
        if relation in ("chain",):
            goal = ask("第三步：因果链结构下，你的研究目的是？",
                       [("test", "理论检验——已明确提出中介机制，要分阶段检验"),
                        ("discover", "结构发现——只知大致层级，希望由数据识别具体结构"),
                        ("", "还不确定")], default="")
            if goal == "":
                goal = None

    names = input("\n结果变量名（英文逗号分隔，可留空）： ").strip() or None
    cnames = input("前因条件名（逗号分隔，可留空）： ").strip() or None
    cases = ask_int("有效案例数 N（可留空跳过检查）： ", default=None)
    conds = ask_int("前因条件数 k（可留空跳过检查）： ", default=None)
    data = ask("数据形态：",
               [("fuzzy", "模糊集"), ("crisp", "清晰集"),
                ("multivalue", "多值集"), ("continuous", "连续变量，尚未校准")],
               default="fuzzy")
    necessity = ask("是否存在明确的必要性假设（某条件可能是「缺了就不行」的瓶颈）？",
                    [("none", "没有或尚未考虑"), ("hypothesis", "有")], default="none")

    return dict(outcomes=outcomes, relation=relation, goal=goal, data=data,
                cases=cases, conds=conds, necessity=necessity,
                outcome_names=names, condition_names=cnames)


# ---------------------------------------------------------------- CLI

def main(argv=None):
    p = argparse.ArgumentParser(
        description="CCM 方法选型辅助工具（结果关系结构导向）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例：\n"
               "  python select_method.py\n"
               "  python select_method.py --question net-effect\n"
               "  python select_method.py --outcomes 2 --relation conjunctive "
               "--cases 600 --conditions 5 --data fuzzy\n")
    p.add_argument("--question", choices=["configurational", "net-effect"],
                   default="configurational",
                   help="前置判断：configurational=条件组态问题（默认）；"
                        "net-effect=平均净效应问题（不属 CCM，直接给出结论）")
    p.add_argument("--outcomes", type=str, help="结果数量：1 / 2 / many")
    p.add_argument("--relation", choices=sorted(RELATION_LABEL),
                   help="多个结果之间的关系")
    p.add_argument("--goal", choices=["test", "discover"],
                   help="因果链结构下的研究目的：test=理论检验，discover=结构发现")
    p.add_argument("--data", choices=sorted(DATA_LABEL), default="fuzzy",
                   help="数据形态（默认 fuzzy）")
    p.add_argument("--cases", type=int, help="有效案例数 N")
    p.add_argument("--conditions", type=int, help="前因条件数 k")
    p.add_argument("--necessity", choices=["none", "hypothesis"], default="none",
                   help="是否存在必要性假设")
    p.add_argument("--outcome-names", type=str, help="结果变量名，逗号分隔")
    p.add_argument("--condition-names", type=str, help="前因条件名，逗号分隔")
    p.add_argument("--json", action="store_true", help="输出 JSON")
    a = p.parse_args(argv)

    net = a.question == "net-effect"
    if not net and a.outcomes is None:
        kw = interactive()
        net = bool(kw.pop("_net_effect", False))
    elif not net:
        if a.outcomes == "1":
            outcomes = 1
        elif a.outcomes in ("2", "many") or a.outcomes.isdigit():
            outcomes = 2 if a.outcomes == "2" else 3
        else:
            p.error("--outcomes 只能是 1 / 2 / many")
            return 2
        if outcomes > 1 and not a.relation:
            p.error("结果多于一个时必须指定 --relation（independent / conjunctive / chain / common / mixed）")
            return 2
        kw = dict(outcomes=outcomes, relation=a.relation, goal=a.goal, data=a.data,
                  cases=a.cases, conds=a.conditions, necessity=a.necessity,
                  outcome_names=a.outcome_names, condition_names=a.condition_names)
    if net:                                   # 前置判断不过 → 不进 CCM 选型
        kw = dict(outcomes=None, relation=None, goal=None, data=a.data, cases=a.cases,
                  conds=a.conditions, necessity=a.necessity,
                  outcome_names=a.outcome_names, condition_names=a.condition_names)

    rec = not_ccm() if net else recommend(**kw)

    if a.json:
        print(json.dumps({"input": dict(kw, question="net-effect" if net else "configurational"),
                          "recommendation": rec}, ensure_ascii=False, indent=2))
    else:
        print(render(rec, kw["data"], kw["cases"], kw["conds"]))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (KeyboardInterrupt, EOFError):
        print("\n已中断。")
        sys.exit(130)
