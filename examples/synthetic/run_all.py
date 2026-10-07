# -*- coding: utf-8 -*-
"""一键复跑合成示范：造数 -> 校准 -> fsQCA/CNA -> CORA。

用法：cd examples/synthetic && python run_all.py

解释器路径可用环境变量覆盖：
  RSCRIPT     默认依次尝试 rscript / Rscript / Rscript.exe 以及常见安装位置
  CORA_PYTHON 默认用当前解释器（若它已装 cora）

CORA 与 QCA/CNA 依赖不同环境时（CORA 需 Python + cora 包，QCA/CNA 需 R），
分别把 CORA_PYTHON 与 RSCRIPT 指到各自的可执行文件即可，例如：
  RSCRIPT="/c/Program Files/R/R-4.6.1/bin/Rscript.exe" \
  CORA_PYTHON="C:/Users/me/cora_env/Scripts/python.exe" python run_all.py
"""
import io
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
R_CANDIDATES = [
    os.environ.get("RSCRIPT"), "Rscript", "Rscript.exe", "rscript",
    r"C:\Program Files\R\R-4.6.1\bin\Rscript.exe",
    "/c/Program Files/R/R-4.6.1/bin/Rscript.exe",
]


def find_rscript():
    for c in R_CANDIDATES:
        if not c:
            continue
        p = shutil.which(c) or (c if os.path.exists(c) else None)
        if p:
            return p
    return None


def run(label, cmd):
    print("=" * 66)
    print("[%s]  %s" % (label, " ".join(str(c) for c in cmd)))
    print("=" * 66)
    r = subprocess.run(cmd, cwd=HERE)
    if r.returncode != 0:
        print("\n!! 步骤「%s」失败（退出码 %d）" % (label, r.returncode))
        sys.exit(r.returncode)


def main():
    py = sys.executable
    rscript = find_rscript()
    cora_py = os.environ.get("CORA_PYTHON", py)

    if rscript is None:
        print("找不到 Rscript。请设置环境变量 RSCRIPT 指向 Rscript 可执行文件，例如：\n"
              '  RSCRIPT="/c/Program Files/R/R-4.6.1/bin/Rscript.exe" python run_all.py')
        sys.exit(1)

    run("1/4 造数", [py, "make_data.py"])
    run("2/4 校准", [py, "prepare.py"])
    run("3/4 fsQCA + CNA", [rscript, "run_analysis.R"])
    run("4/4 CORA", [cora_py, "run_cora.py"])

    print("\n全部完成。结果在 output/ 下：")
    for f in sorted(os.listdir(os.path.join(HERE, "output"))):
        print("  output/" + f)


if __name__ == "__main__":
    main()
