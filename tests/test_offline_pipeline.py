"""合成正反例：驗證資料粒度、日曆 Lag、唯讀與真正 CLI 入口。"""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from src.pipeline.data_pipeline import build_frame
from src.pipeline.input_validation import InputValidationError
from src.pipeline.offline_demo import create_demo_inputs
from src.pipeline.thesis_stats import bootstrap_spearman, main as stats_main


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def inputs(tmp_path):
    return create_demo_inputs(tmp_path / "合成 輸入 #1")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_valid_pipeline_preserves_inputs_and_calendar_meaning(inputs):
    db, stock = inputs
    before = [digest(db), digest(stock)]
    result = build_frame(db, stock)
    assert result.index.equals(pd.date_range("2025-03-27", "2025-04-16", name="Date"))
    assert result.Period.value_counts().to_dict() == {"P1": 7, "P2": 7, "P3": 7}
    assert result.R_daily.notna().sum() == 13
    assert result.iloc[0].Total == 6
    assert result.iloc[0].Pos_prop == pytest.approx(1 / 6)
    assert result.iloc[0].R_daily == pytest.approx(-0.02)
    assert result.loc["2025-04-05", "Total"] == 11
    assert pd.isna(result.loc["2025-04-05", "R_daily"])
    assert result.loc["2025-04-07", "Momentum_2"] == pytest.approx(2 / 12 - 5 / 11)
    assert result.loc["2025-04-07", "Momentum_2"] != pytest.approx(2 / 12 - 1 / 9)
    np.testing.assert_allclose(result[["Pos_prop", "Neg_prop", "Neu_prop"]].sum(axis=1), 1)
    assert [digest(db), digest(stock)] == before


@pytest.mark.parametrize("fault, expected", [
    ("duplicate", "Date 重複"),
    ("reversed", "Date 必須遞增"),
    ("zero", "大於零"),
    ("infinity", "有限"),
    ("missing_price", "有限"),
    ("no_previous", "研究起日前"),
    ("missing_end", "研究首日或末日"),
    ("bad_header", "欄位"),
    ("bad_date", "YYYY/MM/DD"),
])
def test_reject_stock_corruption(inputs, fault, expected):
    db, path = inputs
    frame = pd.read_csv(path, encoding="cp950")
    if fault == "duplicate":
        frame = pd.concat([frame, frame.iloc[[2]]], ignore_index=True)
    elif fault == "reversed":
        frame = frame.iloc[::-1]
    elif fault in ("zero", "infinity", "missing_price"):
        frame["收盤價"] = frame["收盤價"].astype(float)
        frame.loc[2, "收盤價"] = {"zero": 0, "infinity": np.inf, "missing_price": np.nan}[fault]
    elif fault == "no_previous":
        frame = frame.iloc[1:]
    elif fault == "missing_end":
        frame = frame.iloc[:-1]
    elif fault == "bad_header":
        frame = frame.rename(columns={"收盤價": "錯誤欄名"})
    else:
        frame.loc[2, "Date"] = "not-a-date"
    frame.to_csv(path, index=False, encoding="cp950")
    with pytest.raises(InputValidationError, match=expected):
        build_frame(db, path)


@pytest.mark.parametrize("sql, expected", [
    ("UPDATE ai_model_predictions_v2_push_only SET label_id=9 WHERE rowid=1", "label_id"),
    ("UPDATE ai_model_predictions_v2_push_only SET timestamp='bad' WHERE rowid=1", "無法解析"),
    ("UPDATE ai_model_predictions_v2_push_only SET timestamp='2025-04-05T12:00:00+08:00' WHERE rowid=1", "不帶時區"),
    ("UPDATE ai_model_predictions_v2_push_only SET label_id=NULL WHERE timestamp='04/05 12:00'", "2025-04-05"),
    ("ALTER TABLE ai_model_predictions_v2_push_only RENAME COLUMN label_id TO wrong", "需要 timestamp"),
])
def test_reject_prediction_corruption(inputs, sql, expected):
    db, stock = inputs
    with sqlite3.connect(db) as conn:
        conn.execute(sql)
    with pytest.raises(InputValidationError, match=expected):
        build_frame(db, stock)


def test_missing_database_is_not_created(inputs):
    _, stock = inputs
    missing = stock.parent / "typo.db"
    with pytest.raises(InputValidationError, match="不存在"):
        build_frame(missing, stock)
    assert not missing.exists()


def test_bootstrap_repeats_without_touching_global_rng():
    frame = pd.DataFrame({"x": [1, 3, 5, 2, 4, 6], "y": [4, 3, 6, 2, 5, 1]})
    state = np.random.get_state()
    first = bootstrap_spearman(frame, "x", "y", n=80)
    assert first == bootstrap_spearman(frame, "x", "y", n=80)
    after = np.random.get_state()
    assert state[0] == after[0]
    np.testing.assert_array_equal(state[1], after[1])
    assert state[2:] == after[2:]
    assert first != bootstrap_spearman(frame, "x", "y", n=80, seed=7)
    monotonic = pd.DataFrame({"x": [1, 2, 3, 4], "y": [10, 20, 30, 40]})
    assert bootstrap_spearman(monotonic, "x", "y", n=80) == pytest.approx((1, 1, 1))


@pytest.mark.parametrize("x,y", [([1, 1, 1], [1, 2, 3]), ([1, 2], [2, 1]), ([], [])])
def test_undefined_bootstrap_returns_nan(x, y):
    result = bootstrap_spearman(pd.DataFrame({"x": x, "y": y}), "x", "y", n=10)
    assert all(np.isnan(value) for value in result)


def test_zero_draws_rejected():
    with pytest.raises(ValueError, match="正整數"):
        bootstrap_spearman(pd.DataFrame({"x": [1, 2, 3], "y": [3, 2, 1]}), "x", "y", n=0)


def test_absent_sentiment_class_is_not_reported_as_significant(inputs, tmp_path):
    db, stock = inputs
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE ai_model_predictions_v2_push_only SET label_id=1")
    csv_path = tmp_path / "neutral.csv"
    build_frame(db, stock).to_csv(csv_path)
    report = tmp_path / "nested" / "stats.txt"
    stats_main(csv_path, report, data_kind="SYNTHETIC")
    text = report.read_text(encoding="utf-8")
    assert "卡方檢定與 Cramer's V 無法估計" in text
    assert "rho=nan (), 95% CI=[nan, nan]" in text


def run_cli(*args, env=None):
    return subprocess.run(
        [sys.executable, str(ROOT / "run_pipeline.py"), *map(str, args)],
        cwd=ROOT, env=env or {**os.environ, "PYTHONUTF8": "1"},
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )


def test_cli_demo_is_offline_reproducible_and_refuses_overwrite(tmp_path):
    # 子程序實際載入 socket 封鎖器；不是只檢查程式碼沒有網路 import。
    guard = tmp_path / "guard"
    guard.mkdir()
    (guard / "sitecustomize.py").write_text(
        "import os, socket\nfrom pathlib import Path\n"
        "def denied(*args, **kwargs):\n    raise RuntimeError('NETWORK_DISABLED')\n"
        "socket.socket.connect = denied\nsocket.socket.connect_ex = denied\n"
        "socket.create_connection = denied\nsocket.getaddrinfo = denied\n"
        "Path(os.environ['OFFLINE_GUARD_MARKER']).write_text('active')\n", encoding="utf-8"
    )
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONPATH": str(guard),
           "OFFLINE_GUARD_MARKER": str(tmp_path / "guard-active"),
           "DB_PATH_M": "DO_NOT_USE.db", "STOCK_CSV": "DO_NOT_USE.csv",
           "OUTPUT_CSV": "DO_NOT_WRITE.csv", "STATS_OUTPUT": "DO_NOT_WRITE.txt"}
    probe = subprocess.run(
        [sys.executable, "-c", "import socket; socket.create_connection(('127.0.0.1', 9))"],
        cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", timeout=10,
    )
    assert probe.returncode != 0 and "NETWORK_DISABLED" in probe.stderr
    runs = [tmp_path / "run 1", tmp_path / "run 2"]
    for target in runs:
        result = run_cli("--demo", "--output-dir", target, env=env)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "SYNTHETIC" in result.stdout
    assert (tmp_path / "guard-active").read_text() == "active"
    for name in ("synthetic-daily.csv", "synthetic-statistics.txt", "receipt.json"):
        assert (runs[0] / name).read_bytes() == (runs[1] / name).read_bytes()
    receipt = json.loads((runs[0] / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["historical_results_reproduced"] is False
    for name, sha in receipt["sha256"].items():
        assert digest(runs[0] / name) == sha
    before = {path.name: digest(path) for path in runs[0].iterdir()}
    result = run_cli("--demo", "--output-dir", runs[0])
    assert result.returncode == 2
    assert {path.name: digest(path) for path in runs[0].iterdir()} == before


def test_cli_check_only_writes_nothing_and_failure_preserves_result(inputs, tmp_path):
    db, stock = inputs
    output = tmp_path / "must-not-exist"
    result = run_cli("--check-only", "--db", db, "--stock-csv", stock, "--output-dir", output)
    assert result.returncode == 0, result.stderr
    assert "21 個日曆日，13 筆日報酬" in result.stdout
    assert not output.exists()
    output.mkdir()
    sentinel = output / "thesis_final_data.csv"
    sentinel.write_bytes(b"existing result must survive invalid input")
    stock.write_text("Date,wrong\n2025/03/27,100\n", encoding="cp950")
    result = run_cli("--db", db, "--stock-csv", stock, "--output-dir", output)
    assert result.returncode == 2
    assert "欄位" in result.stderr
    assert sentinel.read_bytes() == b"existing result must survive invalid input"
    assert not (output / "THESIS_FULL_TABLES.txt").exists()
