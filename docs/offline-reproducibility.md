# 離線 pipeline 工程驗證

【有來源】這個入口呼叫目前的資料處理與統計模組。論文、歷史資料、模型評分與 [ERRATA](../ERRATA.md) 保持原樣。0.683 有訓練／測試重疊與反覆看測試分數調整的問題；45 筆 holdout 的 0.580 也不能代表市場預測能力。本文不宣稱重現這兩個分數。

## 1. 安裝最小環境

【實測】Windows、CPython 3.13.1；版本鎖定於 `requirements-offline.txt`。其他 Python／作業系統尚未驗證。套件安裝需要 PyPI 或事先備妥的 wheel；**安裝後** demo、輸入檢查與測試不需網路。沒有 Torch、Transformers、模型下載或爬蟲。

所有 PowerShell 指令都在自己的 repo 根目錄執行；以下使用相對路徑，不需啟用 venv 或改執行原則。

```powershell
python -m venv venv
$env:PYTHONUTF8 = '1'
& '.\venv\Scripts\python.exe' -m pip install -r requirements-offline.txt
& '.\venv\Scripts\python.exe' -m pytest -vv
```

【實測】舊測試 18 項與第一輪新增的 24 個案例均保留、不放寬；安全回歸另放在 `tests/test_pipeline_safety.py`。涵蓋日曆 Lag、來源雜湊、輸入正反例、退化統計、真正 CLI 的 Python socket／DNS 封鎖執行，以及硬連結、排他建立的插入競態、完整時間格式與 WAL 邊界。此為工程測試，不是模型效果評測。

## 2. 不需要私有資料的 demo

```powershell
& '.\venv\Scripts\python.exe' run_pipeline.py --demo --output-dir '.\outputs\offline-demo-01'
```

輸出目錄必須不存在；再次執行請改用另一個新目錄，程式不覆蓋既有 demo。成功 exit code 為 0，輸出：

- `SYNTHETIC.txt`：合成資料聲明。
- `synthetic.db`、`synthetic-stock.csv`：人工設定的 21 天留言與 13 天價格，加一個研究期前的收盤價。
- `synthetic-daily.csv`：21 列、每期 7 天；假日保留留言，報酬為缺值。
- `synthetic-statistics.txt`：明示 `SYNTHETIC`、seed、各相關係數的有效 N；不等同論文表格。
- `receipt.json`：輸入／輸出 SHA-256、seed 42、1,000 次 bootstrap，及 `historical_results_reproduced: false`。

【實測】相同鎖定環境與 seed 的兩次 demo，處理後 CSV、統計報告與 receipt 位元組一致。沒有啟動 server、瀏覽器或 UI，也沒有產生截圖。

## 3. 只檢查自己已有的本機研究資料

以下路徑只是預期位置，乾淨 clone **沒有**這兩份研究輸入。先執行唯讀檢查：

```powershell
& '.\venv\Scripts\python.exe' run_pipeline.py --check-only --db '.\database\ptt_data.db' --stock-csv '.\data\raw\taiex_open_close.csv'
```

`--check-only` 計算並檢查輸入，但不建立輸出目錄或報告；SQLite 使用 `mode=ro`，路徑拼錯不會建立空 DB。失敗 exit code 為 2，stderr 會說明原因。檢查通過只表示符合以下契約，不等於資料真實、完整或研究成立。

【唯讀邊界】`mode=ro` 保護主資料庫內容，不代表來源目錄零寫入。WAL 資料庫在讀取時可能建立或更新 `-wal`／`-shm` 側檔，驗證失敗也可能留下側檔；這與 CSV／統計輸出無關。本程式不主動 checkpoint、不修改 journal mode，也不使用會忽略未 checkpoint 資料的 `immutable=1`。若需要來源目錄完全不變，請先由資料擁有人提供一致的離線快照；本入口不提供該保證。

要產生目前 pipeline 的結果，移除 `--check-only` 並加 `--output-dir` 指向另存結果的目錄。**行為變更：真實資料模式也拒絕覆寫任何既有同名輸出，請每次選用新路徑。** 既有目錄可用，但兩個結果檔都必須不存在。`--db`、`--stock-csv` 優先於既有 `.env` 設定；不提供參數時仍沿用 `DB_PATH_M`、`STOCK_CSV`、`OUTPUT_CSV`、`STATS_OUTPUT`。`--output-dir` 同時決定 CSV 與統計文字檔的位置。demo 的路徑由參數明確指定，不使用上述環境變數。

輸入與兩個結果會檢查解析路徑及既有檔案身分（含 NTFS 硬連結）。完整驗證與統計先在記憶體完成，再以排他建立 `open("x")` 取得全部輸出控制代碼，才寫入內容；不會在預檢後另用 `open("w")` 重開檔案。預檢後插入同名檔案也會拒絕，已保留的空檔會按身分清理，既有結果保持原樣。兩個模組的 `main()` 入口同樣拒絕覆寫。

【限制】這不是跨檔案的 crash-atomic 交易；磁碟滿、程序中止或清理失敗可能留下本次新檔。輸入與輸出目錄須由操作者控制；不保證抵禦惡意程序在開啟後改換父目錄、重新連結已開啟檔案，或同步修改來源內容。正常的既有硬連結與建立前插入競態已有回歸測試。

## 4. 輸入契約與失敗界線

| 輸入 | 檢查 | 原因 |
|---|---|---|
| SQLite | `ai_model_predictions_v2_push_only` 含 `timestamp`、`label_id` | 與既有 pipeline 查詢一致 |
| 標籤 | 非 NULL 的值只能為 0／1／2；NULL 延續原有排除規則 | 避免未知類別進入總數卻未進入三類比例 |
| 時間 | 完整匹配 `MM/DD HH:MM`（固定 2025 年）、`YYYY-MM-DD`／`YYYY/MM/DD`（可加空白或 T 與時分）；時間可有秒及 1–9 位小數秒。來源須為無時區的台灣本地時間 | 驗證秒／日期合法性；不截去尾碼，不猜測時區 |
| 情緒日曆 | 2025-03-27 至 2025-04-16 每天都須有非 NULL 預測 | `Momentum_2` 的差兩列才能代表兩個日曆日；不把缺日填成零留言 |
| 股價 CSV | cp950、`Date` 為 YYYY/MM/DD、`收盤價` 為有限正數 | 不自動填補或修補表頭 |
| 股價粒度 | 日期唯一且已遞增 | 避免 join 放大與報酬順序錯置 |
| 股價邊界 | 含研究起日前一筆價格及研究首末日 | 不把首日日報酬當成零 |

【限制】沒有內建官方交易日曆，因此無法判斷中間某個交易日是否漏資料，也無法確認前置價格確實屬於緊鄰的上一交易日。檢查只回報有幾筆報酬，不強迫所有輸入為 13 天。重複留言是否屬於真實不同留言，也不能只靠 timestamp／label_id 判定。

【行為變更】任何非 NULL 預測的壞時間或未知標籤（包含研究期外資料）都會停止，要求操作者先確認來源；不自動改資料。缺日、重複日期等問題在寫出 CSV 前被拒絕。原本缺少輸出資料夾的正常執行，現在會自動建立資料夾。

時間的 `Z`、`+08:00`、`-12:00` 或 `+0800` 等 offset 會保留給時區驗證並被拒絕，不會截去後當成本地時間。`03/27 12:00INVALID`、`03/27 12:00:99`、`03/27 23:30-12:00` 均 exit 2，不寫新結果、也不覆寫舊結果。合法的 MM/DD、ISO、完整日期與小數秒有相容回歸；不接受未列出的模糊自由文字日期格式。

## 5. 統計與歷史結果的邊界

- bootstrap 改用局部 `RandomState(seed)`；預設 42，可用 `--seed` 指定 0 至 4294967295。保留成對重抽樣與百分位區間算法，不污染其他程式的全域亂數。
- 少於三個有效配對、常數序列或抽樣後沒有可定義的係數，區間回傳 `nan`；卡方表的列／欄總和為零也標示無法估計，不報顯著。
- `Momentum_2` 仍是 21 日完整日曆上的正面比例差，不改成交易日 Lag。假日股價不填值；首日日報酬使用輸入檔的前一列價格。
- 累積報酬仍從**股價 CSV 的第一列**為基準，延續既有算法；提供更多前期價格會影響基準。本次沒有另改研究期間的報酬定義。
- 目前 pipeline 的結構表是卡方檢定；它沒有實作 ERRATA 中所有 ANOVA、Tukey、敏感度或模型評估。demo 成功不能表示論文表格或勘誤數字重現成功。
- ERRATA 於 2026-10 記錄「未固定 seed」是當時的狀態；本次僅修目前 `src/pipeline/thesis_stats.py` 的後續執行，歷史檔案與 `scripts/` 原始實驗腳本不變。

【未驗證】本機原始 DB／CSV、模型權重與研究分數；其他平台；Web／桌面標註工具。不要以合成資料結果宣稱預測能力。
