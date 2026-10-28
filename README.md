# PTT Stock Sentiment and the TAIEX

**A three-person NTNU study that fine-tuned a multilingual BERT on PTT Stock comments and event-studied retail sentiment against the TAIEX during the April 2025 U.S. reciprocal-tariff shock.**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

The question: when tariff headlines hit in late March and April 2025, did talk on Taiwan’s largest retail forum change shape, move with the index, and carry a short-horizon reversal or volatility signal?

📊 **[Poster](docs/presentations/poster.pdf)** · 📝 **[Thesis](docs/papers/thesis.md)** · 🎨 **[Flowchart](docs/presentations/research_flowchart.pdf)** · ⚠️ **[Errata](ERRATA.md)**

> **Re-checked in October 2026.** Several numbers and claims in the submitted thesis do not match the project's own data. The thesis is kept as submitted; corrections, recomputed values and evidence are in [ERRATA.md](ERRATA.md). The summary below uses the corrected values.

---

## English summary

National Taiwan Normal University undergraduate capstone (學習科學學士學位學程), three-person team. Advisors: 李良一, 吳清麟. Window: 27 March–16 April 2025, split into pre-event (P1, 27 Mar–2 Apr), shock (P2, 3–9 Apr), and suspension / post-event (P3, 10–16 Apr; 暫緩期).

**Method.** Crawl → clean → label → fine-tune BERT → evaluate → event study.

1. Crawl PTT Stock posts and pushes.
2. Clean timestamps and text, and align forum text with TAIEX daily data (`yfinance` in the study; a local CSV in the pipeline).
3. Label sentiment in three classes (positive / neutral / negative). Three annotators labeled 300 comments, 150 titles and 150 post bodies; 2-of-3 majority was kept and three-way disagreements were resolved by arbitration. Fleiss’ κ was 0.5509 on comments, 0.4452 on post bodies, and 0.2377 on titles, so training used comments only. (The thesis prints 0.6509 for comments and says disagreements were dropped; see [ERRATA](ERRATA.md).)
4. Fine-tune `nlptown/bert-base-multilingual-uncased-sentiment` (PyTorch, Hugging Face Transformers). V1 was fine-tuned from nlptown; V2 continued from V1 on comments only, with 493 training items (185 / 159 / 149) and 90 validation items (30 per class). Most V2 items were labeled by one person.
5. Compare V0, V1, and V2 on a balanced test set of 210 comments, then run inference with V2. Macro-F1: V0 0.475, V1 0.232, V2 0.683 (thesis Table 3-3, reproduced exactly). That test set overlaps the V2 training data and was used while tuning V2; on a 45-item held-out split labeled by three-annotator consensus, V2 scores 0.580.
6. Event study on two samples: all 21 calendar days for the sentiment-structure tests, and 13 trading days for the market correlations (Spearman, with a 1,000-draw bootstrap).

**What the data support.** Values below were recomputed from the project's local data in October 2026 ([ERRATA](ERRATA.md) lists every difference from the thesis). This is one event, and every market correlation is same-day, so none of it shows prediction.

- **The sentiment mix shifted in the shock week.** Neutral share rose from 0.3266 (P1) to 0.3743 (P2) and positive share fell from 0.1713 to 0.1396; both changes hold under Tukey correction (p = 0.023 and 0.020). Classic ANOVA gives p < 0.03 for all three shares, but Welch's ANOVA, which allows for the unequal variances, gives p = 0.05–0.08. No significant change from P2 to P3, so there is no evidence of a rebound in confidence. Mean daily discussion volume went from 8,275 (P1) to 29,185 (P2).
- **Positive and negative shares both moved with the index; neutral moved against it.** Spearman against cumulative TAIEX return on 13 trading days: positive ρ = 0.588 (p = 0.035), negative ρ = +0.560 (p = 0.046), neutral ρ = −0.484 (p = 0.094). The thesis prints −0.560 for negative and reads the result as a bull/bear mirror; that reading is wrong. The correlation mostly reflects the three periods sitting at different levels; in daily changes it drops to ρ = 0.13.
- **The "Lag-2 momentum" result does not hold up.** ρ = 0.782 (N = 11) appears only when the lag is counted in trading days after dropping non-trading days, which spans 2–6 calendar days around the holiday. Counted as two calendar days, as the thesis defines it, ρ = −0.255, p = 0.45. It was also the best of many specifications tried.
- **Discussion volume tracked same-day volatility.** Volume vs absolute return: ρ = 0.714, p = 0.006 (the thesis's 0.736 used a first-day return wrongly set to 0). Volume did not predict the next day's absolute return (ρ = 0.17, p = 0.60).

**Stack.** Python, Requests, BeautifulSoup, SQLite, PyTorch, Hugging Face Transformers, pandas, NumPy, SciPy, Matplotlib, Flask, Tkinter, `yfinance`. Base checkpoint: `nlptown/bert-base-multilingual-uncased-sentiment`.

**How to run.** Databases matching `*.db` and CSV files are gitignored, so a fresh clone cannot rerun the market pipeline until those local files exist.

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Statistics pipeline expects database/ptt_data_m.db and data/raw/taiex_open_close.csv
# unless DB_PATH_M and STOCK_CSV say otherwise. See .env.example.
# Web app needs FLASK_SECRET_KEY in .env.
pip install -r requirements.txt
cp .env.example .env
python run_pipeline.py

python run_web_app.py          # http://localhost:8000
python run_desktop_app.py

# Fine-tune (scripts/finetune_bert.py). Training JSON is under ptt_raw_consensus/.
```

Labeled JSON already in the repo: `ptt_raw_consensus/`, `ptt_raw_consensus_push_only/`, `ptt_gold_standard/`.

### Representative result

Thesis Figure 4-1: Z-scored daily positive-comment share on PTT Stock and Z-scored TAIEX cumulative return over the same window. The matching rank test is Spearman ρ = 0.588, p = 0.035, N = 13.

![Z-scored positive PTT Stock sentiment and Z-scored TAIEX cumulative return, 27 Mar–16 Apr 2025](docs/papers/figures/figure_03.png)

*Figure 4-1 from [docs/papers/thesis.md](docs/papers/thesis.md). Source file: `docs/papers/figures/figure_03.png`.*

### Team

Three-person team project. Roles as listed in the thesis appendix (小組分工情形):

| Member | Role |
|---|---|
| 王語揚 Roy Wang ([theroyatlas](https://github.com/theroyatlas)) | Data crawling, BERT model training, coding, statistical analysis |
| 呂筱婕 | Research design, charts, presentation and poster design |
| 林峻霆 | Literature review, research framework, data annotation, conclusions and final integration |

All three members took part in the three-annotator labeling round.

---

## 中文說明

## PTT 情緒分析與股市關聯研究系統

> 一個整合 NLP 情緒分析、人工標註工具與統計檢定的完整研究平台

📊 **[查看專題海報](docs/presentations/poster.pdf)** | 📝 **[閱讀論文](docs/papers/thesis.md)** | 🎨 **[研究流程圖](docs/presentations/research_flowchart.pdf)**

論文標題：事件驅動下的網路社群情緒與市場表現：以川普關稅政策期間之 PTT 股票版與台股加權指數為例。

---

## 📌 專案動機 (Motivation)

本專案旨在探討「PTT 股票板情緒」與「台股大盤走勢」之間的關聯性。透過：

1. **自動化爬蟲** — 收集 PTT Stock 板文章與推文
2. **BERT 情緒分類** — 微調 `nlptown/bert-base-multilingual-uncased-sentiment`，做正面 / 中性 / 負面三分類
3. **人工標註系統** — Web 與桌面雙介面，支援多人協作標註
4. **統計檢定** — 變異數分析、Spearman 相關、Bootstrap 信賴區間

最終產出論文用的統計表格與視覺化圖表。

> ⚠️ **2026-10 重新檢查後的勘誤。**論文保留繳交時的原樣，但其中有數個數字與結論和專案資料不符，例如：H2 負面情緒相關實為 +0.560（論文寫 −0.560）、留言 Kappa 為 0.5509（論文寫 0.6509）、V2 訓練集為 493 筆（論文寫 750）、「兩日情緒動能」換成論文自己的日曆日定義後不顯著，以及測試集與訓練資料有重疊。完整更正與證據見 [ERRATA.md](ERRATA.md)。

---

## 🚀 快速啟動 (Quick Start)

操作步驟的較短版本在 [QUICKSTART.md](QUICKSTART.md)。

### 1. 環境需求

- Python 3.8+
- SQLite 3
- （選用）CUDA，用於 GPU 微調

### 2. 安裝依賴

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

`*.db` 與 `*.csv` 在 `.gitignore` 裡。重跑 pipeline 需要本機的 `database/ptt_data_m.db` 與 `data/raw/taiex_open_close.csv`（路徑可用環境變數改）。

### 3. 設定環境變數

```bash
cp .env.example .env
# 至少設定 FLASK_SECRET_KEY（只在啟動網頁標註時需要）
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. 執行資料處理 Pipeline

```bash
python run_pipeline.py
```

等同依序執行 `src/pipeline/data_pipeline.py` 與 `src/pipeline/thesis_stats.py`。

### 5. 啟動標註系統

#### Web 介面（多人協作）

```bash
python run_web_app.py
# http://localhost:8000
```

#### 桌面介面（單人標註）

```bash
python run_desktop_app.py
```

---

## 🏗️ 系統架構 (Architecture)

```
使用者 → Flask Web App → SQLite Database
                ↓
         BERT 模型推論 → 情緒標籤
                ↓
         統計分析模組 → 論文表格/圖表
```

| 模組 | 功能 | 技術棧 |
|------|------|--------|
| `web_app/` | 多人標註系統 | Flask + Jinja2 + SQLite |
| `desktop_app/` | 桌面標註工具 | Tkinter + SQLite |
| `pipeline/` | 資料處理流程 | Pandas + NumPy + SciPy |
| `scripts/` | 實驗性分析腳本 | 爬蟲、微調、統計與視覺化 |

細部說明見 [docs/architecture.md](docs/architecture.md)。

---

## 📊 資料流程 (Data Pipeline)

```mermaid
graph LR
    A[PTT 爬蟲] --> B[原始文本]
    B --> C[BERT 情緒分類]
    C --> D[人工標註驗證]
    D --> E[統計分析]
    E --> F[論文表格/圖表]
```

1. **資料收集** — 爬取 PTT Stock 板指定期間的文章
2. **情緒分類** — 微調 `nlptown/bert-base-multilingual-uncased-sentiment`（論文第 3.3.3 節）。後續推論使用 V2
3. **人工標註** — Web / Desktop 介面，三分制。訓練語料只用留言
4. **統計檢定** — 全日曆日 N = 21 的結構比較，與交易日 N = 13 的 Spearman 相關、Bootstrap CI
5. **視覺化** — Z-score、MinMax、Diff 等對照圖，圖檔在 `assets/charts/` 與 `docs/papers/figures/`

---

## 🔧 技術棧 (Tech Stack)

- **語言與介面**: Python 3、Flask、Tkinter
- **資料庫**: SQLite 3（爬蟲腳本另有 PostgreSQL 路徑）
- **NLP**: PyTorch、Hugging Face Transformers；基礎模型 `nlptown/bert-base-multilingual-uncased-sentiment`
- **資料與統計**: pandas、NumPy、SciPy；股價取得使用 `yfinance`
- **視覺化**: Matplotlib、Seaborn
- **爬蟲**: Requests、BeautifulSoup

---

## 📁 專案結構 (Project Structure)

```
ptt-sentiment-stock-analysis/
├── src/                          # pipeline、標註程式、db 工具
├── scripts/                      # 爬蟲、微調、事件研究與繪圖
├── ptt_raw_consensus/            # 標註後 JSON（train / validation / test）
├── ptt_raw_consensus_push_only/
├── ptt_gold_standard/
├── assets/charts/                # 研究圖
├── docs/                         # 論文、海報、架構說明
├── data/                         # 本地 raw / processed（CSV 不進版控）
├── database/                     # 本地 SQLite（*.db 不進版控）
└── tests/
```

---

## 🔐 安全性注意事項 (Security)

1. 不要 commit `.env`
2. 不要在程式碼裡硬編碼密碼或 API key
3. `*.db` 已在 `.gitignore`
4. Flask `SECRET_KEY` 用 `secrets.token_hex(32)` 產生

---

## 📈 使用範例 (Usage Examples)

### 範例 1：取得資料庫連線

```python
from src.utils.db_utils import get_conn

conn = get_conn()
rows = conn.execute("SELECT COUNT(*) FROM sentiments").fetchone()
print(f"文章總數：{rows[0]}")
conn.close()
```

### 範例 2：查詢標註進度

```python
from src.utils.db_utils import get_conn

conn = get_conn()
rows = conn.execute(
    "SELECT label_id, COUNT(*) FROM manual_labels_articles_all GROUP BY label_id"
).fetchall()
for label_id, count in rows:
    print(f"label_id={label_id}: {count} 筆")
conn.close()
```

這兩個查詢假設本機資料庫裡已有對應資料表。

---

## 🤝 貢獻指南 (Contributing)

1. Fork 本專案
2. 建立功能分支 (`git checkout -b feature/AmazingFeature`)
3. Commit (`git commit -m 'Add some AmazingFeature'`)
4. Push (`git push origin feature/AmazingFeature`)
5. 開啟 Pull Request

---

## 📝 授權條款 (License)

MIT License。見 [LICENSE](LICENSE)。

---

## 👤 作者 (Author)

- **研究者**: 王語揚、呂筱婕、林峻霆
- **指導教授**: 李良一、吳清麟
- **機構**: 國立臺灣師範大學 學習科學學士學位學程

| 成員 | 分工（論文附錄） |
|---|---|
| 王語揚 | BERT 模型訓練、程式撰寫、資料爬蟲、統計分析 |
| 呂筱婕 | 研究設計、圖表繪製、簡報與海報設計 |
| 林峻霆 | 文獻探討、研究架構設計、數據標註、結論撰寫與統整 |
- **聯絡方式**: jg971402@gmail.com

---

## 🙏 致謝 (Acknowledgments)

- [Hugging Face](https://huggingface.co/) 上的 `nlptown/bert-base-multilingual-uncased-sentiment`，以及 Transformers 函式庫
- PTT 社群提供的公開討論

---

## 📚 相關論文 (Related Papers)

- 📊 [專題海報](docs/presentations/poster.pdf)
- 📝 [論文全文](docs/papers/thesis.md)
- 🎨 [研究流程圖](docs/presentations/research_flowchart.pdf)

```bibtex
@misc{ptt-sentiment-2025,
  author = {王語揚 and 呂筱婕 and 林峻霆},
  title = {事件驅動下的網路社群情緒與市場表現：以川普關稅政策期間之 PTT 股票版與台股加權指數為例},
  year = {2025},
  publisher = {GitHub},
  url = {https://github.com/theroyatlas/ptt-sentiment-stock-analysis}
}
```

---

**最後更新**: 2026-10-14
