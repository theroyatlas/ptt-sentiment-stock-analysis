"""Synthetic regression cases for output identity, complete timestamps and WAL."""
from contextlib import closing
import hashlib
import os
from pathlib import Path
import sqlite3

import pandas as pd
import pytest

from src.pipeline import data_pipeline, thesis_stats
from src.pipeline.input_validation import InputValidationError, read_predictions
from src.pipeline.offline_demo import create_demo_inputs
from src.pipeline.output_safety import write_new_outputs
from tests.test_offline_pipeline import run_cli


NAMES = ("thesis_final_data.csv", "THESIS_FULL_TABLES.txt")
INVALID_TIMES = [
    "03/27 12:00INVALID", "03/27 12:00:99", "03/27 23:30-12:00",
    "03/27 12:00Z", "03/27 12:00+08:00",
    "2025-03-27T12:00:00+08:00", "2025-03-27T12:00:00-12:00",
    "2025-03-27T12:00:00Z", "2025-03-27T12:00:99",
    "2025-03-27T12:00:00INVALID", "03/27 12:00+08:99",
    "03/27 12:00:00ZINVALID", "03/27 24:00", "02/30 12:00",
]
VALID_TIMES = [
    "03/27 12:00", "03/27 00:00", "03/27 23:59",
    "03/27 12:00:59", "03/27 12:00:59.123456789",
    "2025-03-27T12:00:00", "2025-03-27T12:00",
    "2025-03-27 12:00:59.123456", "2025/03/27 12:00:00",
    "2025-03-27", "2025/03/27",
]


@pytest.fixture
def inputs(tmp_path):
    return create_demo_inputs(tmp_path / "合成 輸入 #1%")


def hashes(paths):
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def assert_sqlite(db):
    assert db.read_bytes()[:16] == b"SQLite format 3\0"
    with closing(sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone() == ("ok",)


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("source_index", [0, 1])
def test_cli_rejects_output_hardlink_to_either_source(inputs, tmp_path, name, source_index):
    db, stock = inputs
    output = tmp_path / "results"
    output.mkdir()
    alias = output / name
    os.link(inputs[source_index], alias)
    assert alias.samefile(inputs[source_index])
    before = hashes([db, stock, alias])
    result = run_cli("--db", db, "--stock-csv", stock, "--output-dir", output)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "同一檔案" in result.stderr
    assert hashes([db, stock, alias]) == before
    assert_sqlite(db)
    assert {p.name for p in output.iterdir()} == {name}


@pytest.mark.parametrize("kind", ["first", "second", "both", "hardlinked_pair"])
def test_cli_refuses_existing_results_even_with_valid_inputs(inputs, tmp_path, kind):
    db, stock = inputs
    output = tmp_path / "results"
    output.mkdir()
    first, second = [output / name for name in NAMES]
    if kind in ("first", "both", "hardlinked_pair"):
        first.write_bytes(b"prior CSV must survive")
    if kind in ("second", "both"):
        second.write_bytes(b"prior statistics must survive")
    if kind == "hardlinked_pair":
        os.link(first, second)
        assert first.samefile(second)
    existing = list(output.iterdir())
    before = hashes([db, stock, *existing])
    result = run_cli("--db", db, "--stock-csv", stock, "--output-dir", output)
    assert result.returncode == 2, result.stdout + result.stderr
    assert hashes([db, stock, *existing]) == before
    assert set(output.iterdir()) == set(existing)
    assert_sqlite(db)


@pytest.mark.parametrize("target_index", [0, 1])
@pytest.mark.parametrize("source_index", [0, 1])
def test_exclusive_open_blocks_hardlink_inserted_after_precheck(inputs, tmp_path, monkeypatch, target_index, source_index):
    outputs = [tmp_path / name for name in NAMES]
    target = outputs[target_index]
    before = hashes(inputs)
    original_open = Path.open
    injected = []

    def racing_open(path, mode="r", *args, **kwargs):
        if path == target and mode == "x":
            os.link(inputs[source_index], target)
            injected.append(target)
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", racing_open)
    with pytest.raises(FileExistsError):
        write_new_outputs([(p, "must never be written") for p in outputs], sources=inputs)
    assert injected == [target]
    assert hashes(inputs) == before
    assert target.samefile(inputs[source_index])
    assert not outputs[1 - target_index].exists()
    assert_sqlite(inputs[0])


def test_exclusive_open_blocks_second_output_aliasing_reserved_first(tmp_path, monkeypatch):
    first, second = [tmp_path / name for name in NAMES]
    original_open = Path.open

    def racing_open(path, mode="r", *args, **kwargs):
        if path == second and mode == "x":
            os.link(first, second)
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", racing_open)
    with pytest.raises(FileExistsError):
        write_new_outputs([(first, "CSV"), (second, "statistics")])
    assert not first.exists()  # only our placeholder was removed
    assert second.read_bytes() == b""  # competing link was never written/deleted


def test_same_output_path_and_direct_source_alias_are_rejected(inputs, tmp_path):
    before = hashes(inputs)
    with pytest.raises(InputValidationError, match="同一檔案"):
        write_new_outputs([(inputs[0], "bad")], sources=inputs)
    target = tmp_path / "same"
    with pytest.raises(InputValidationError, match="同一檔案"):
        write_new_outputs([(target, "first"), (target, "second")], sources=inputs)
    assert not target.exists()
    assert hashes(inputs) == before


@pytest.mark.parametrize("value", INVALID_TIMES)
def test_invalid_complete_timestamp_cli_exit2_preserves_sources(inputs, tmp_path, value):
    db, stock = inputs
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("UPDATE ai_model_predictions_v2_push_only SET timestamp=? WHERE rowid=1", (value,))
        conn.commit()
    before = hashes(inputs)
    output = tmp_path / "new-results"
    result = run_cli("--db", db, "--stock-csv", stock, "--output-dir", output)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "timestamp" in result.stderr
    assert not output.exists()
    assert hashes(inputs) == before
    assert_sqlite(db)
    # Invalid input must also preserve both previous results.
    output.mkdir()
    existing = [output / name for name in NAMES]
    for path in existing:
        path.write_bytes(b"existing result")
    old_results = hashes(existing)
    result = run_cli("--db", db, "--stock-csv", stock, "--output-dir", output)
    assert result.returncode == 2 and "timestamp" in result.stderr
    assert hashes(existing) == old_results
    assert hashes(inputs) == before


@pytest.mark.parametrize("value", VALID_TIMES)
def test_complete_valid_timestamp_preserves_calendar(inputs, value):
    db, stock = inputs
    baseline = data_pipeline.build_frame(db, stock)
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("UPDATE ai_model_predictions_v2_push_only SET timestamp=? WHERE rowid=1", (value,))
        conn.commit()
    before = hashes(inputs)
    pd.testing.assert_frame_equal(data_pipeline.build_frame(db, stock), baseline)
    assert hashes(inputs) == before


@pytest.mark.parametrize("value", ["03/27 23:30-12:00", "2025-03-27T12:00:00+08:00", "2025-03-27T12:00:00Z"])
def test_parser_preserves_timezone_for_validator(value):
    assert data_pipeline.fix_timestamp(value).tzinfo is not None


def test_fresh_cli_output_succeeds_then_refuses_rerun(inputs, tmp_path):
    db, stock = inputs
    before = hashes(inputs)
    output = tmp_path / "new-results"
    result = run_cli("--db", db, "--stock-csv", stock, "--output-dir", output)
    assert result.returncode == 0, result.stdout + result.stderr
    assert set(p.name for p in output.iterdir()) == set(NAMES)
    assert len(pd.read_csv(output / NAMES[0])) == 21
    assert "LOCAL_INPUT" in (output / NAMES[1]).read_text(encoding="utf-8")
    result_hashes = hashes(list(output.iterdir()))
    result = run_cli("--db", db, "--stock-csv", stock, "--output-dir", output)
    assert result.returncode == 2
    assert hashes(list(output.iterdir())) == result_hashes
    assert hashes(inputs) == before
    assert_sqlite(db)


def test_module_entrypoints_share_no_clobber_protection(inputs, tmp_path):
    db, stock = inputs
    daily = tmp_path / "daily.csv"
    stats = tmp_path / "stats.txt"
    data_pipeline.main(db, stock, daily)
    thesis_stats.main(daily, stats)
    before = hashes([db, stock, daily, stats])
    with pytest.raises(InputValidationError, match="已存在"):
        data_pipeline.main(db, stock, daily)
    with pytest.raises(InputValidationError, match="已存在"):
        thesis_stats.main(daily, stats)
    assert hashes([db, stock, daily, stats]) == before
    alias = tmp_path / "source-alias.csv"
    os.link(db, alias)
    with pytest.raises(InputValidationError, match="同一檔案"):
        data_pipeline.main(db, stock, alias)
    stats_alias = tmp_path / "daily-alias.txt"
    os.link(daily, stats_alias)
    with pytest.raises(InputValidationError, match="同一檔案"):
        thesis_stats.main(daily, stats_alias)
    assert hashes([db, stock, daily, stats]) == before


@pytest.mark.parametrize("invalid", [False, True])
def test_wal_readonly_main_file_can_create_sidecars(inputs, tmp_path, invalid):
    db, stock = inputs
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("PRAGMA journal_mode=WAL").fetchone() == ("wal",)
        if invalid:
            conn.execute("UPDATE ai_model_predictions_v2_push_only SET label_id=9 WHERE rowid=1")
            conn.commit()
    sidecars = [Path(str(db) + suffix) for suffix in ("-wal", "-shm")]
    assert not any(p.exists() for p in sidecars)
    before = hashes(inputs)
    output = tmp_path / "not-created"
    result = run_cli("--check-only", "--db", db, "--stock-csv", stock, "--output-dir", output)
    assert result.returncode == (2 if invalid else 0), result.stderr
    assert hashes(inputs) == before
    assert not output.exists()
    assert all(p.exists() for p in sidecars)


def test_readonly_reader_sees_committed_uncheckpointed_wal(inputs):
    db, stock = inputs
    with closing(sqlite3.connect(db)) as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("PRAGMA wal_autocheckpoint=0")
        before = hashes(inputs)
        writer.execute("INSERT INTO ai_model_predictions_v2_push_only VALUES ('03/27 12:00', 9)")
        writer.commit()
        assert Path(str(db) + "-wal").stat().st_size > 0
        assert hashes(inputs) == before  # the new row is only in WAL
        assert 9 in read_predictions(db).label_id.values
        with pytest.raises(InputValidationError, match="label_id"):
            data_pipeline.build_frame(db, stock)
        assert hashes(inputs) == before
