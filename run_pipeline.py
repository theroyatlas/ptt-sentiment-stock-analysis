#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
資料處理 Pipeline 執行腳本
"""
import argparse
import hashlib
import json
from io import StringIO
from pathlib import Path
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description="離線 PTT 統計 pipeline；不下載資料或模型。")
    parser.add_argument("--demo", action="store_true", help="用合成資料驗證流程，非研究結果")
    parser.add_argument("--db", type=Path, help="本機情緒 SQLite；以唯讀方式開啟")
    parser.add_argument("--stock-csv", type=Path, help="本機 cp950 股價 CSV")
    parser.add_argument("--output-dir", type=Path, help="輸出目錄；demo 必填且不可已存在")
    parser.add_argument("--check-only", action="store_true", help="僅驗證與計算，不寫入任何結果")
    parser.add_argument("--seed", type=int, default=42, help="bootstrap seed，預設 42")
    args = parser.parse_args(argv)
    if not 0 <= args.seed < 2**32:
        parser.error("--seed 必須介於 0 與 4294967295")
    if args.demo and (args.db or args.stock_csv or args.check_only or not args.output_dir):
        parser.error("--demo 需 --output-dir，且不能搭配 --db、--stock-csv 或 --check-only")

    from src.pipeline import data_pipeline, thesis_stats
    from src.pipeline.input_validation import InputValidationError
    from src.pipeline.offline_demo import create_demo_inputs
    from src.pipeline.output_safety import write_new_outputs

    try:
        if args.demo:
            db_path, stock_csv = create_demo_inputs(args.output_dir)
            output_csv = args.output_dir / "synthetic-daily.csv"
            stats_file = args.output_dir / "synthetic-statistics.txt"
        else:
            db_path = args.db or Path(data_pipeline.DB_PATH)
            stock_csv = args.stock_csv or Path(data_pipeline.STOCK_CSV)
            output_csv = (args.output_dir / "thesis_final_data.csv" if args.output_dir
                          else Path(data_pipeline.OUTPUT_CSV))
            stats_file = (args.output_dir / "THESIS_FULL_TABLES.txt" if args.output_dir
                          else Path(thesis_stats.OUTPUT_FILE))
        if args.check_only:
            frame = data_pipeline.build_frame(db_path, stock_csv)
            print(f"驗證通過：{len(frame)} 個日曆日，{frame['R_daily'].notna().sum()} 筆日報酬；未寫入結果。")
            print("此檢查不驗證交易日完整性、來源真實性、模型品質或歷史研究數值。")
            return 0
        # Validate and render both results before reserving either output.
        # Statistics consume the same CSV bytes, without reopening a pathname
        # that could have been replaced since writing the daily result.
        frame = data_pipeline.build_frame(db_path, stock_csv)
        csv_text = frame.to_csv(lineterminator="\n")
        kind = "SYNTHETIC" if args.demo else "LOCAL_INPUT"
        report = thesis_stats.render_report(StringIO(csv_text), seed=args.seed, data_kind=kind)
        write_new_outputs([(output_csv, csv_text), (stats_file, report)],
                          sources=[db_path, stock_csv])
        if args.demo:
            receipt = {
                "data_kind": kind, "historical_results_reproduced": False,
                "bootstrap_seed": args.seed, "bootstrap_draws": 1000,
                "sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                           for path in (db_path, stock_csv, output_csv, stats_file)},
            }
            (args.output_dir / "receipt.json").write_text(
                json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        print(f"完成：{kind}；結果目錄 {output_csv.resolve().parent}")
        return 0
    except (InputValidationError, OSError) as exc:
        print(f"輸入或檔案錯誤：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
