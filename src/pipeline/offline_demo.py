"""只建立合成輸入；數值不是 PTT 或台股的觀測結果。"""
from datetime import date, timedelta
from pathlib import Path
import csv
import sqlite3


def create_demo_inputs(directory):
    directory = Path(directory)
    # 不覆蓋任何既有目錄；CLI / 測試每次使用新的路徑。
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "SYNTHETIC.txt").write_text(
        "合成資料：僅驗證程式流程，不是研究資料，也不是歷史結果重現。\n",
        encoding="utf-8",
    )
    db_path = directory / "synthetic.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE ai_model_predictions_v2_push_only (timestamp TEXT, label_id INTEGER)")
        for i in range(21):
            day = date(2025, 3, 27) + timedelta(days=i)
            for label, count in enumerate((2 + i % 3, 3 + i % 4, 1 + i % 5)):
                conn.executemany(
                    "INSERT INTO ai_model_predictions_v2_push_only VALUES (?, ?)",
                    [(day.strftime("%m/%d 12:00"), label)] * count,
                )
    stock_path = directory / "synthetic-stock.csv"
    # 13 個研究期交易日 + 一個前置收盤價；全部價格皆人工設定。
    days = ["2025/03/26", "2025/03/27", "2025/03/28", "2025/03/31",
            "2025/04/01", "2025/04/02", "2025/04/07", "2025/04/08",
            "2025/04/09", "2025/04/10", "2025/04/11", "2025/04/14",
            "2025/04/15", "2025/04/16"]
    closes = [100, 98, 101, 99, 102, 100, 95, 97, 96, 101, 103, 102, 105, 104]
    with stock_path.open("w", encoding="cp950", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Date", "收盤價"])
        writer.writerows(zip(days, closes))
    return db_path, stock_path
