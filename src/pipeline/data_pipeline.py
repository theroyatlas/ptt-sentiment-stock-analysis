# 檔案名稱: data_pipeline.py
import pandas as pd
import numpy as np
import os
import re
from pathlib import Path
from dotenv import load_dotenv
from src.pipeline.input_validation import read_predictions, read_stock, validate_predictions
from src.pipeline.output_safety import write_new_outputs

# 載入環境變數
load_dotenv()

# --- 設定 ---
DB_PATH = os.getenv("DB_PATH_M", "database/ptt_data_m.db")
STOCK_CSV = os.getenv("STOCK_CSV", "data/raw/taiex_open_close.csv")
OUTPUT_CSV = os.getenv("OUTPUT_CSV", "data/processed/thesis_final_data.csv")

# 嚴格定義日期 (21天)
P1_DATES = pd.date_range('2025-03-27', '2025-04-02')
P2_DATES = pd.date_range('2025-04-03', '2025-04-09')
P3_DATES = pd.date_range('2025-04-10', '2025-04-16')
ALL_DATES = pd.date_range('2025-03-27', '2025-04-16')

def fix_timestamp(ts_str):
    if not isinstance(ts_str, str): return pd.NaT
    value = ts_str.strip()
    # Match the whole value, including seconds and offset. Never discard a
    # suffix: validate_predictions must still see any parsed timezone.
    clock = r'[0-9]{2}:[0-9]{2}(?::[0-9]{2}(?:\.[0-9]{1,9})?)?'
    zone = r'(?:Z|[+-](?:[01][0-9]|2[0-3]):?[0-5][0-9])?'
    if re.fullmatch(r'[0-9]{2}/[0-9]{2}\s' + clock + zone, value):
        value = '2025/' + value
    elif not re.fullmatch(
        r'[0-9]{4}(?:-[0-9]{2}-[0-9]{2}|/[0-9]{2}/[0-9]{2})'
        r'(?:[T\s]' + clock + zone + r')?', value
    ):
        return pd.NaT
    return pd.to_datetime(value, errors='coerce')

def build_frame(db_path, stock_csv):
    """驗證並計算 21 個日曆日；主 DB 唯讀、不寫結果，WAL 可產生側檔。"""
    # 1. 讀取情緒資料 (含假日)
    df_sent = validate_predictions(read_predictions(db_path), fix_timestamp, ALL_DATES)
    
    # 2. 統計每日計數
    daily = df_sent.groupby(['Date', 'label_id']).size().unstack(fill_value=0)
    for c in [0, 1, 2]: 
        if c not in daily.columns: daily[c] = 0
    daily.rename(columns={0:'Count_Neg', 1:'Count_Neu', 2:'Count_Pos'}, inplace=True)
    
    daily['Total'] = daily.sum(axis=1)
    daily['Pos_prop'] = daily['Count_Pos'] / daily['Total']
    daily['Neg_prop'] = daily['Count_Neg'] / daily['Total']
    daily['Neu_prop'] = daily['Count_Neu'] / daily['Total']
    daily.index = pd.to_datetime(daily.index)
    
    # 3. 讀取並合併股價
    df_stock = read_stock(stock_csv, ALL_DATES)
    df_stock['R_daily'] = df_stock['收盤價'].pct_change(fill_method=None)
    df_stock['Cumulative_Return'] = (1 + df_stock['R_daily'].fillna(0)).cumprod() - 1
    
    # 合併 (Left join 保留假日情緒)
    df_final = daily.join(df_stock, how='left')
    
    # 4. 篩選 21 天並標註 Period
    df_final = df_final.loc[df_final.index.isin(ALL_DATES)].copy()
    
    conditions = [df_final.index.isin(P1_DATES), df_final.index.isin(P2_DATES), df_final.index.isin(P3_DATES)]
    df_final['Period'] = np.select(conditions, ['P1', 'P2', 'P3'], default='Other')
    
    # 5. 計算高階指標 (Momentum, Volatility, Volume Ratio)
    df_final['Momentum_2'] = df_final['Pos_prop'].diff(2) # Lag-2 動能
    df_final['Abs_R_daily'] = df_final['R_daily'].abs()   # 波動率
    
    p1_avg_vol = df_final[df_final['Period']=='P1']['Total'].mean()
    df_final['Vol_Ratio'] = df_final['Total'] / p1_avg_vol # 量能倍數
    df_final['Total_Surge'] = df_final['Total'].diff()     # 量能變化
    
    return df_final


def main(db_path=None, stock_csv=None, output_csv=None):
    print("🚀 [Step 1] 啟動資料生成 pipeline...")
    df_final = build_frame(db_path or DB_PATH, stock_csv or STOCK_CSV)
    output = Path(output_csv or OUTPUT_CSV)
    write_new_outputs([(output, df_final.to_csv(lineterminator="\n"))],
                      sources=[db_path or DB_PATH, stock_csv or STOCK_CSV])
    print(f"✅ 資料已生成：{output} (共 {len(df_final)} 天)")
    return df_final

if __name__ == "__main__":
    main()
