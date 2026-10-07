## 合成示范：栏1 fsQCA（单一结果）+ 栏2 fuzzy CNA（因果链）
##
## 用法：cd examples/synthetic && Rscript run_analysis.R
##   （本机 Rscript 常不在 PATH 上，写全路径，例如
##    "/c/Program Files/R/R-4.6.1/bin/Rscript.exe" run_analysis.R）
## 前置：make_data.py -> prepare.py 已生成 data_fuzzy.csv
## 注：脚本内变量名一律 ASCII，中文列名只在写文件时套用。
suppressMessages(library(QCA)); suppressMessages(library(cna))
dir.create("output", showWarnings = FALSE)
cat("QCA", as.character(packageVersion("QCA")), "| cna", as.character(packageVersion("cna")),
    "| R", R.version.string, "\n")

d <- read.csv("data_fuzzy.csv", fileEncoding = "UTF-8")
K <- c("P1_fiscal", "P2_talent", "P3_digital", "P4_cluster", "P5_openness")
COND6 <- c(K, "M_collab")
NCUT <- 2          # 频数阈值：600 案例 / 64 真值表行，平均每行约 9 家，取 2 过滤薄行

## ==================== 栏1 fsQCA：6 条件 -> Y_perf ====================
d1 <- d[complete.cases(d[, c(COND6, "Y_perf")]), ]
d1 <- d1[abs(d1$Y_perf - 0.5) > 1e-9, ]
cat("== 栏1 fsQCA  n =", nrow(d1), " k =", length(COND6), "==\n")
for (inc in c(0.70, 0.75, 0.80)) {
  tt <- truthTable(d1, outcome = "Y_perf", conditions = COND6,
                   incl.cut = inc, n.cut = NCUT, pri.cut = 0.70)
  cx <- minimize(tt, details = TRUE, use.tilde = TRUE)                 # 复杂解
  pr <- try(minimize(tt, include = "?", details = FALSE), silent = TRUE) # 简约解
  it <- try(minimize(tt, include = "?", dir.exp = rep("1", length(COND6)),
                     details = FALSE), silent = TRUE)                   # 中间解
  fmt <- function(x) if (inherits(x, "try-error")) "ERROR" else paste(x$solution[[1]], collapse = " + ")
  cat(sprintf("  incl.cut=%.2f  真值表 %d 行，OUT=1 行 %d，计入案例 %d（n = %d）\n", inc,
      nrow(tt$tt), sum(as.numeric(as.character(tt$tt$OUT)) == 1, na.rm = TRUE),
      sum(as.numeric(as.character(tt$tt$n)), na.rm = TRUE), nrow(d1)))
  cat("    复杂解:", fmt(cx), "\n")
  cat("    简约解:", fmt(pr), "\n")
  cat("    中间解:", fmt(it), "\n")
  if (inc == 0.75) {
    ic <- round(cx$IC$incl.cov[, c("inclS", "PRI", "covS", "covU")], 3)
    print(ic); print(round(cx$IC$sol.incl.cov, 3))
    out <- data.frame(路径 = rownames(ic), 一致性inclS = ic$inclS, PRI = ic$PRI,
                      原始覆盖covS = ic$covS, 唯一覆盖covU = ic$covU)
    out <- rbind(out, data.frame(路径 = "总体解",
                      一致性inclS = round(cx$IC$sol.incl.cov$inclS, 3),
                      PRI = round(cx$IC$sol.incl.cov$PRI, 3),
                      原始覆盖covS = round(cx$IC$sol.incl.cov$covS, 3), 唯一覆盖covU = NA))
    write.csv(out, "output/fsqca_paths.csv", row.names = FALSE, fileEncoding = "UTF-8")
  }
}

## ==================== 必要性初检（对 Y_perf）====================
g5 <- d[, c(K, "M_collab", "Y_perf")]
nec <- NULL
for (k in c(K, "M_collab")) {
  t <- pof("Y_perf", k, data = g5, relation = "necessity")$incl.cov
  nec <- rbind(nec, data.frame(cond = k, inclN = round(t$inclN, 4),
                               covN = round(t$covN, 4), RoN = round(t$RoN, 4)))
}
cat("\n== 必要性初检 ==\n"); print(nec, row.names = FALSE)
cat("最高必要性一致度 =", sprintf("%.4f", max(nec$inclN)), "（", nec$cond[which.max(nec$inclN)],
    "）；全部 < 0.90 -> 无必要瓶颈\n")
names(nec) <- c("条件", "必要性一致度inclN", "必要性覆盖度covN", "RoN")
write.csv(nec, "output/necessity.csv", row.names = FALSE, fileEncoding = "UTF-8")

## ==================== 栏2 fuzzy CNA：前因5 < M_collab < Y_perf ====================
g <- d[, c(K, "M_collab", "Y_perf")]
cat("\n== 栏2 fuzzy CNA  n =", nrow(g), "==\n")
ordering <- "P1_fiscal,P2_talent,P3_digital,P4_cluster,P5_openness < M_collab < Y_perf"
cnt <- NULL
for (con in c(0.70, 0.75, 0.80)) {
  m <- cna(g, outcome = c("M_collab", "Y_perf"), ordering = ordering,
           strict = TRUE, suff.only = TRUE, con = c(con), cov = c(0.35))
  key <- sprintf("con%03d", round(con * 100))
  if (file.exists(sprintf("output/cna_%s.csv", key))) file.remove(sprintf("output/cna_%s.csv", key))
  for (oc in c("M_collab", "Y_perf")) {
    s <- m$solution[[toupper(oc)]]$msc            # 注意：cna() 把结果名转为大写
    o <- order(-as.numeric(s$con))
    cat(sprintf("-- con=%.2f  OUT %s : %d 项 --\n", con, oc, nrow(s)))
    for (r in head(o, 4)) cat(sprintf("   %-34s con=%.4f cov=%.4f\n",
        as.character(s$condition[r]), as.numeric(s$con[r]), as.numeric(s$cov[r])))
    cnt <- rbind(cnt, data.frame(con = con, outcome = oc, n_items = nrow(s)))
    df <- if (nrow(s) == 0) {
      data.frame(outcome = character(0), condition = character(0),
                 con = numeric(0), cov = numeric(0))
    } else {
      data.frame(outcome = oc, condition = as.character(s$condition[o]),
                 con = round(as.numeric(s$con[o]), 4), cov = round(as.numeric(s$cov[o]), 4))
    }
    f <- sprintf("output/cna_%s.csv", key)
    prev <- if (file.exists(f)) read.csv(f, fileEncoding = "UTF-8") else NULL
    write.csv(rbind(prev, df), f, row.names = FALSE, fileEncoding = "UTF-8")
  }
}
names(cnt) <- c("阈值con", "结果", "最小充分条件项数")
write.csv(cnt, "output/cna_counts.csv", row.names = FALSE, fileEncoding = "UTF-8")
cat("\n[已落盘] output/：fsqca_paths.csv、necessity.csv、cna_con0{70,75,80}.csv、cna_counts.csv\n")
