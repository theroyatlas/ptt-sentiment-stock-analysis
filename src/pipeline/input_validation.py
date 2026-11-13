"""研究 pipeline 的輸入契約；拒絕錯誤資料，不補值或改寫來源。"""
from contextlib import closing
from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd


class InputValidationError(ValueError):
    """可由 CLI 顯示給使用者的輸入錯誤。"""


def read_predictions(db_path):
    """Read the main DB without SQL writes; SQLite WAL may create -wal/-shm.

    Do not use immutable=1: it can ignore committed, uncheckpointed WAL data.
    A missing DB is rejected before connecting, not created as an empty file.
    """
    path = Path(db_path).resolve()
    if not path.is_file():
        raise InputValidationError(f"情緒資料庫不存在：{path}；請指定 --db，或使用 --demo。")
    try:
        # mode=ro 避免 SQLite 在路徑拼錯時建立空資料庫。
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as conn:
            return pd.read_sql_query(
                "SELECT timestamp, label_id FROM ai_model_predictions_v2_push_only "
                "WHERE label_id IS NOT NULL", conn
            )
    except (sqlite3.Error, pd.errors.DatabaseError) as exc:
        raise InputValidationError(
            "無法讀取 ai_model_predictions_v2_push_only；需要 timestamp、label_id 欄位。"
        ) from exc


def validate_predictions(frame, parse_timestamp, all_dates):
    if frame.empty:
        raise InputValidationError("情緒資料沒有非 NULL 的預測標籤。")
    if not frame["label_id"].isin([0, 1, 2]).all():
        raise InputValidationError("label_id 僅允許 0=負面、1=中性、2=正面。")
    frame = frame.copy()
    parsed = frame["timestamp"].apply(parse_timestamp)
    if parsed.isna().any():
        raise InputValidationError(f"情緒 timestamp 無法解析：{int(parsed.isna().sum())} 筆；不會靜默刪除。")
    if any(getattr(value, "tzinfo", None) is not None for value in parsed):
        raise InputValidationError("timestamp 必須是台灣本地時間且不帶時區；請先確認來源的時區。")
    frame["Date"] = pd.to_datetime(parsed).dt.normalize()
    missing = all_dates.difference(frame["Date"])
    if len(missing):
        dates = ", ".join(missing.strftime("%Y-%m-%d"))
        raise InputValidationError(f"21 天情緒資料缺日：{dates}；不補零，避免 Lag-2 變成跨列位移。")
    return frame


def read_stock(stock_csv, all_dates):
    path = Path(stock_csv).resolve()
    if not path.is_file():
        raise InputValidationError(f"股價 CSV 不存在：{path}")
    try:
        frame = pd.read_csv(path, encoding="cp950", usecols=["Date", "收盤價"])
        if frame.empty:
            raise ValueError("空檔")
        if not frame["Date"].astype(str).str.fullmatch(r"\d{4}/\d{2}/\d{2}").all():
            raise ValueError("日期格式")
        frame["Date"] = pd.to_datetime(frame["Date"], format="%Y/%m/%d", errors="raise")
        frame["收盤價"] = pd.to_numeric(frame["收盤價"], errors="raise")
    except (ValueError, UnicodeError, pd.errors.ParserError) as exc:
        raise InputValidationError("股價 CSV 需 cp950 編碼、Date（YYYY/MM/DD）與數值收盤價欄位。") from exc
    if frame["Date"].duplicated().any():
        raise InputValidationError("股價 Date 重複；每日只能有一列，避免 join 放大留言數。")
    if not frame["Date"].is_monotonic_increasing:
        raise InputValidationError("股價 Date 必須遞增；不自動重排，以免改變報酬計算。")
    if not (np.isfinite(frame["收盤價"]) & (frame["收盤價"] > 0)).all():
        raise InputValidationError("收盤價必須為有限且大於零的數值；不填補缺值。")
    if frame["Date"].iloc[0] >= all_dates[0]:
        raise InputValidationError("股價需包含研究起日前的收盤價，才能計算首日日報酬。")
    if not {all_dates[0], all_dates[-1]}.issubset(set(frame["Date"])):
        raise InputValidationError("股價缺少研究首日或末日（2025-03-27、2025-04-16）。")
    return frame.set_index("Date")
