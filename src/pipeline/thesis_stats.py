# 檔案名稱: thesis_stats.py
import pandas as pd
import numpy as np
import scipy.stats as stats
import os
from pathlib import Path
from io import StringIO
from dotenv import load_dotenv
from src.pipeline.output_safety import write_new_outputs

# 載入環境變數
load_dotenv()

INPUT_CSV = os.getenv("OUTPUT_CSV", "data/processed/thesis_final_data.csv")
OUTPUT_FILE = os.getenv("STATS_OUTPUT", "data/outputs/THESIS_FULL_TABLES.txt")

def get_sig(p):
    if p < 0.01: return "***"
    if p < 0.05: return "**"
    if p < 0.1: return "*"
    return ""

def bootstrap_spearman(df, x, y, n=1000, seed=42):
    """成對重抽樣；使用局部 RNG，不更動呼叫端的亂數狀態。"""
    if isinstance(n, bool) or not isinstance(n, (int, np.integer)) or n <= 0:
        raise ValueError("bootstrap n 必須為正整數")
    data = df[[x, y]].dropna()
    if len(data) < 3: return np.nan, np.nan, np.nan
    if data[x].nunique() < 2 or data[y].nunique() < 2:
        return np.nan, np.nan, np.nan
    rng = np.random.RandomState(seed)
    rs = []
    for _ in range(n):
        sample = data.sample(n=len(data), replace=True, random_state=rng)
        if sample[x].nunique() < 2 or sample[y].nunique() < 2:
            continue
        r, _ = stats.spearmanr(sample[x], sample[y])
        if not np.isnan(r): rs.append(r)
    if not rs: return np.nan, np.nan, np.nan
    return np.mean(rs), np.percentile(rs, 2.5), np.percentile(rs, 97.5)

def render_report(input_csv=None, seed=42, data_kind="LOCAL_INPUT"):
    """Render the unchanged statistics in memory before any output is created."""
    df = pd.read_csv(input_csv or INPUT_CSV, parse_dates=['Date'], index_col='Date')

    with StringIO() as f:
        f.write(f"資料種類：{data_kind}；bootstrap seed={seed}，n=1000；nan 表示無法估計。\n")
        f.write("此為目前 pipeline 輸出，不等同論文或 ERRATA 歷史數值重現；不支持預測力宣稱。\n\n")
        # 1. 描述統計
        f.write("【表 4-1：描述性統計】\n")
        cols = ['Pos_prop', 'Neg_prop', 'Neu_prop', 'Total', 'R_daily']
        f.write(f"{'Variable':<15} | {'P1 (Mean±Std)':<20} | {'P2 (Mean±Std)':<20} | {'P3 (Mean±Std)':<20}\n")
        f.write("-" * 80 + "\n")
        for c in cols:
            row = f"{c:<15} | "
            for p in ['P1', 'P2', 'P3']:
                sub = df[df['Period']==p][c].dropna()
                row += f"{sub.mean():.4f}±{sub.std():.4f}   | "
            f.write(row + "\n")
        f.write("\n")

        # 2. 卡方檢定 (結構斷裂)
        f.write("【表 4-2：卡方檢定 (結構斷裂)】\n")
        table = df.groupby('Period')[['Count_Pos', 'Count_Neu', 'Count_Neg']].sum().reindex(['P1', 'P2', 'P3'])
        n_total = table.sum().sum()
        if table.sum(axis=0).eq(0).any() or table.sum(axis=1).eq(0).any():
            chi2, p, cramers_v = np.nan, np.nan, np.nan
            f.write("列或欄總數為零，卡方檢定與 Cramer's V 無法估計。\n")
        else:
            chi2, p, _, _ = stats.chi2_contingency(table)
            cramers_v = np.sqrt(chi2 / (n_total * 2))
        f.write(f"Total N: {n_total}\nChi2: {chi2:.4f}\nP-value: {p:.4e}\nCramer's V: {cramers_v:.4f}\n\n")

        # 3. 相關性 (含 Bootstrap)
        f.write("【表 4-3：相關性與 Bootstrap 防禦】\n")
        pairs = [
            ('Pos_prop', 'Cumulative_Return', '正面 vs 趨勢'),
            ('Momentum_2', 'R_daily', '動能(Lag2) vs 報酬'),
            ('Vol_Ratio', 'Abs_R_daily', '量能 vs 波動')
        ]
        for x, y, name in pairs:
            paired = df[[x, y]].dropna()
            if len(paired) < 3 or paired[x].nunique() < 2 or paired[y].nunique() < 2:
                r, p = np.nan, np.nan
            else:
                r, p = stats.spearmanr(paired[x], paired[y])
            mean_boot, lower, upper = bootstrap_spearman(df, x, y, seed=seed)
            f.write(f"{name:<15}: N={len(paired)}, rho={r:.4f} ({get_sig(p)}), 95% CI=[{lower:.4f}, {upper:.4f}]\n")
        return f.getvalue()


def main(input_csv=None, output_file=None, seed=42, data_kind="LOCAL_INPUT"):
    print("🚀 [Step 2] 啟動統計分析...")
    report = render_report(input_csv, seed=seed, data_kind=data_kind)
    output = Path(output_file or OUTPUT_FILE)
    write_new_outputs([(output, report)], sources=[input_csv or INPUT_CSV])
    print(f"✅ 統計表格已生成：{output}")

if __name__ == "__main__":
    main()
