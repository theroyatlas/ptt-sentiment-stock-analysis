# 🚀 快速啟動指南

## 先選擇驗證範圍

乾淨 clone 不含研究用 DB、CSV、模型權重。若要先確認程式可離線執行，請依 [離線重現說明](docs/offline-reproducibility.md) 安裝最小依賴並執行合成資料 demo；它不會重訓、爬資料或重現論文分數。該文件也提供不寫入結果的 `--check-only` 與資料格式契約。

以下為既有完整環境與標註工具路線，需另外準備本機資料；本次離線工程驗證未測 Web／桌面 UI。`requirements.txt` 包含大型模型套件，僅跑 pipeline／測試時改用 `requirements-offline.txt`。

## 完整環境啟動

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 設定環境變數

```bash
# 複製範本
cp .env.example .env

# 編輯 .env，至少要設定：
# FLASK_SECRET_KEY=<使用下面指令生成>
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. 執行應用程式

#### 選項 A：執行資料處理 Pipeline

```bash
python run_pipeline.py
```

這會依序執行：
1. 資料清洗與特徵工程
2. 統計分析與假設檢定

輸出檔案：
- `data/processed/thesis_final_data.csv` - 處理後的資料
- `data/outputs/THESIS_FULL_TABLES.txt` - 統計表格

#### 選項 B：啟動 Web 標註系統

```bash
python run_web_app.py
```

然後開啟瀏覽器訪問：`http://localhost:8000`

功能：
- 多人協作標註
- 固定順序 queue
- 即時進度儀表板

#### 選項 C：啟動桌面標註工具

```bash
python run_desktop_app.py
```

功能：
- 單人標註
- 資料洩露防護
- 即時統計顯示

## 常見問題

### Q: 找不到資料檔案？

A: 確認以下檔案存在：
- `data/raw/taiex_open_close.csv` - 股價資料
- `database/ptt_data_m.db` - 情緒資料庫

### Q: Flask 啟動失敗？

A: 檢查 `.env` 檔案中是否已設定 `FLASK_SECRET_KEY`

### Q: 資料庫錯誤？

A: 確認 `database/` 資料夾存在且有寫入權限

## 下一步

- 閱讀完整文件：[README.md](README.md)
- 了解系統架構：[docs/architecture.md](docs/architecture.md)
- 部署到生產環境：[docs/deployment.md](docs/deployment.md)

## 需要幫助？

- 查看 [Issues](https://github.com/theroyatlas/ptt-sentiment-stock-analysis/issues)
- 閱讀 [文件](docs/)
- 聯絡作者
