# 🎨 專案展示

## 研究成果視覺化

### 專題海報
完整的研究成果展示，包含研究動機、方法論、實驗結果與結論。

📊 **[查看完整海報 PDF](presentations/poster.pdf)**

---

### 研究流程圖
展示從資料收集到統計分析的完整流程。

🎨 **[查看流程圖 PDF](presentations/research_flowchart.pdf)**

---

## 系統截圖

### Web 標註系統
多人協作標註介面，支援固定順序 queue 與即時進度追蹤。

### 桌面標註工具
單人標註工具，具備資料洩露防護功能。

### 資料視覺化
包含 Z-score、MinMax、Diff 等多種標準化方法的對比圖表。

---

## 研究亮點

### 1. 完整的資料處理 Pipeline
- 自動化爬蟲
- BERT 情緒分類
- 人工標註驗證
- 統計分析

### 2. 嚴謹的統計方法
- 卡方檢定（結構斷裂）
- Spearman 相關性分析
- Bootstrap 信賴區間
- 多重假設檢定校正

### 3. 實用的標註系統
- Web 多人協作
- 桌面單人標註
- 資料洩露防護
- 即時統計顯示

---

## 技術棧展示

```
前端: Flask + Jinja2 + Tkinter
後端: Python + SQLite
NLP: Hugging Face Transformers (BERT)
資料處理: Pandas + NumPy + SciPy
視覺化: Matplotlib + Seaborn
```

---

## 作品集展示建議

### LinkedIn 貼文範本

```
🎓 完成了一個完整的 NLP 研究專案！

探討 PTT 股票板情緒與台股走勢的關聯性，使用：
✅ BERT 情緒分類模型
✅ 人工標註系統（Web + Desktop）
✅ 統計檢定（卡方、Spearman、Bootstrap）

技術棧：Python | Flask | Transformers | SQLite
專案連結：https://github.com/theroyatlas/ptt-sentiment-stock-analysis

#NLP #MachineLearning #DataScience #Python
```

### GitHub Profile README

```markdown
## 🔬 Featured Project: PTT Sentiment Analysis

A complete NLP research platform analyzing the correlation between 
PTT Stock board sentiment and Taiwan stock market performance.

- 🤖 BERT-based sentiment classification
- 👥 Multi-user annotation system
- 📊 Statistical hypothesis testing
- 📈 Real-time visualization

[View Project →](https://github.com/theroyatlas/ptt-sentiment-stock-analysis)
```

---

## 演示影片建議

### 影片大綱（5-10 分鐘）

1. **開場** (30 秒)
   - 研究動機與問題陳述

2. **系統展示** (3 分鐘)
   - Web 標註系統操作
   - 桌面工具展示
   - 資料處理 Pipeline

3. **技術亮點** (2 分鐘)
   - BERT 模型微調
   - 統計分析方法
   - 資料洩露防護

4. **研究成果** (2 分鐘)
   - 視覺化圖表
   - 統計檢定結果
   - 研究發現

5. **結語** (30 秒)
   - 未來展望
   - GitHub 連結

---

## 面試準備

### 可能的問題與回答

**Q: 為什麼選擇 BERT 而不是其他模型？**
A: 基礎模型是 Hugging Face 的 `nlptown/bert-base-multilingual-uncased-sentiment`。它是多語言模型，預訓練在產品評論的星級情感上，星級可對應到負面、中性、正面，再針對 PTT 留言做領域微調。論文第 3.3.3 節說明了這個選擇。

**Q: 如何確保標註品質？**
A: 我們實作了多人標註機制，並計算 Cohen's Kappa 評估標註者間一致性。同時建立了資料洩露防護，確保測試集不包含訓練集資料。

**Q: 統計檢定為什麼選擇 Spearman 而非 Pearson？**
A: 因為情緒比例與股價報酬率可能不符合常態分佈，Spearman 作為無母數方法更為穩健。我們也使用 Bootstrap 方法驗證結果的可靠性。

**Q: 專案最大的挑戰是什麼？**
A: 最大挑戰是處理 PTT 的非結構化文本與時間對齊問題。我們開發了完整的資料清洗 Pipeline，並實作了嚴格的時間戳修正邏輯。

---

**更新日期**: 2026-02-26
