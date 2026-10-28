# 📝 論文與研究文件

本資料夾包含專案相關的學術論文與研究文件。

## 檔案清單

### 論文
- **[thesis.md](thesis.md)** - 論文 Markdown 版（可在 GitHub 直接閱讀）
- **[thesis.docx](thesis.docx)** - 論文完整版（原始格式，含完整排版，需下載後以 Word/LibreOffice 開啟）
  - 標題：事件驅動下的網路社群情緒與市場表現：以川普關稅政策期間之 PTT 股票版與台股加權指數為例

### 論文圖表
- **[figures/](figures/)** - 論文中所有圖表（由 thesis.md 自動引用）

## 研究摘要

本研究探討 PTT 股票板的情緒與台股大盤走勢之間的關聯性，透過：

1. 自動化爬蟲收集 PTT Stock 板文章與推文
2. BERT 情緒分類進行三分類（正面/中性/負面）
3. 人工標註系統進行驗證
4. 統計檢定分析（卡方檢定、Spearman 相關性、Bootstrap）

## 引用格式

如果本研究對你有幫助，請引用：

```bibtex
@misc{ptt-sentiment-2025,
  author = {王語揚},
  title = {事件驅動下的網路社群情緒與市場表現：以川普關稅政策期間之 PTT 股票版與台股加權指數為例},
  year = {2025},
  publisher = {GitHub},
  url = {https://github.com/theroyatlas/ptt-sentiment-stock-analysis}
}
```
