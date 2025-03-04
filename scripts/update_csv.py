import pandas as pd
import yfinance as yf
import numpy as np
import requests
import base64
import json
from datetime import datetime
import io
import os

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = "sohamdeshpande"
REPO_NAME = "dashboard"
CSV_FILE_PATH = "data/ADANIENT.NS.csv"
STOCK_NAME = ['ADANIENT.NS',
 'ADANIPORTS.NS',
 'APOLLOHOSP.NS',
 'ASIANPAINT.NS',
 'AXISBANK.NS',
 'BAJAJ-AUTO.NS',
 'BAJFINANCE.NS',
 'BAJAJFINSV.NS',
 'BEL.NS',
 'BPCL.NS',
 'BHARTIARTL.NS',
 'BRITANNIA.NS',
 'CIPLA.NS',
 'COALINDIA.NS',
 'DRREDDY.NS',
 'EICHERMOT.NS',
 'GRASIM.NS',
 'HCLTECH.NS',
 'HDFCBANK.NS',
 'HDFCLIFE.NS',
 'HEROMOTOCO.NS',
 'HINDALCO.NS',
 'HINDUNILVR.NS',
 'ICICIBANK.NS',
 'ITC.NS',
 'INDUSINDBK.NS',
 'INFY.NS',
 'JSWSTEEL.NS',
 'KOTAKBANK.NS',
 'LT.NS',
 'M&M.NS',
 'MARUTI.NS',
 'NTPC.NS',
 'NESTLEIND.NS',
 'ONGC.NS',
 'POWERGRID.NS',
 'RELIANCE.NS',
 'SBILIFE.NS',
 'SHRIRAMFIN.NS',
 'SBIN.NS',
 'SUNPHARMA.NS',
 'TCS.NS',
 'TATACONSUM.NS',
 'TATAMOTORS.NS',
 'TATASTEEL.NS',
 'TECHM.NS',
 'TITAN.NS',
 'TRENT.NS',
 'ULTRACEMCO.NS',
 'WIPRO.NS']

def get_existing_csv(STOCK_NAME):
    # Get the existing CSV from GitHub
    CSV_FILE_PATH = f'''data/{STOCK_NAME}'''
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{CSV_FILE_PATH}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        content = response.json()["content"]
        decoded_content = base64.b64decode(content).decode('utf-8')
        df = pd.read_csv(io.StringIO(decoded_content), index_col=0, parse_dates=True)
        sha = response.json()["sha"]  # Required for updating the file
        return df, sha
    else:
        print("Error fetching CSV:", response.status_code)
        return None, None
    
def get_last_day_data(STOCK_NAME):
    # Fetch latest data for the last day
    stock_data = yf.download(STOCK_NAME, period="2d", interval="1d")
    if isinstance(stock_data.columns, pd.MultiIndex):
        stock_data.columns = stock_data.columns.droplevel(1)
    stock_data.columns.name = None
    return stock_data.tail(1)

def update_indicators(df):
    # Calculate Moving Averages
    df["50_DMA"] = df["Close"].rolling(window=50).mean()
    df["200_DMA"] = df["Close"].rolling(window=200).mean()
    df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()

    # Calculate RSI
    delta = df["Close"].diff(1)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    gain_series = pd.Series(gain, index=df.index)
    loss_series = pd.Series(loss, index=df.index)
    avg_gain = gain_series.rolling(window=14).mean()
    avg_loss = loss_series.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # Calculate VWMA
    df["VWMA_50"] = (df["Close"] * df["Volume"]).rolling(window=50).sum() / df["Volume"].rolling(window=50).sum()

    # Define Buy/Sell Signals
    df["Buy_Signal"] = (df["50_DMA"] > df["200_DMA"]) & (df["RSI"].shift(1) > 30) & (df["RSI"] < 30)
    df["Sell_Signal"] = (df["50_DMA"] < df["200_DMA"]) & (df["RSI"].shift(1) < 70) & (df["RSI"] > 70)

    # Convert Boolean to Labels
    df["Signal"] = df.apply(lambda row: "BUY" if row["Buy_Signal"] else ("SELL" if row["Sell_Signal"] else "HOLD"), axis=1)

    # Fill NaN values
    df.fillna(method="bfill", inplace=True)

    return df

def update_csv_on_github(df, sha):
    # Convert DataFrame to CSV string
    csv_content = df.to_csv()
    encoded_content = base64.b64encode(csv_content.encode()).decode()

    # Create commit data
    commit_data = {
        "message": f"Updated CSV with latest data on {datetime.today().strftime('%Y-%m-%d')}",
        "content": encoded_content,
        "sha": sha,
        "branch": "main"
    }

    # Upload updated CSV to GitHub
    CSV_FILE_PATH = f'''data/{STOCK_NAME}'''
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{CSV_FILE_PATH}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    response = requests.put(url, headers=headers, data=json.dumps(commit_data))

    if response.status_code == 200:
        print("✅ CSV updated successfully on GitHub!")
    else:
        print("❌ Error updating CSV:", response.status_code, response.json())

def main():
    for STOCK in STOCK_NAME:
        df, sha = get_existing_csv(STOCK)
        if df is not None:
            new_data = get_last_day_data(STOCK)
            df = pd.concat([df, new_data]).drop_duplicates()
            df = update_indicators(df)
            update_csv_on_github(df, sha)

if __name__ == "__main__":
    main()