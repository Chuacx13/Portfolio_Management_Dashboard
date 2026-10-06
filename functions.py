import pandas as pd
import numpy as np
import scipy.stats as stats
import yfinance as yf
from constants import CCY

def load_portfolio_data(csv_path='portfolio.csv'):
    df = pd.read_csv(csv_path)
    df['Trade_Date'] = pd.to_datetime(df['Trade_Date'])
    return df

def fetch_market_data(period='5y'):
    ccy_tickers = [
        f'USDCNY=X'
        if ccy == 'USDCNH'
        else f'{ccy}=X' 
        for ccy in CCY
    ]
    data = yf.download(tickers=ccy_tickers, period=period, interval='1d', progress=False)['Close']
    data.columns = data.columns.str.replace('=X', '', regex=False)
    data.columns = data.columns.str.replace('USDCNY', 'USDCNH', regex=False)
    data.dropna()
    return data

def calculate_pnl(portfolio_df, market_df):
    if market_df.empty or portfolio_df.empty:
        return pd.DataFrame()
        
    current_prices = market_df.iloc[-1]
    yst_prices = market_df.iloc[-2]
    onewk_prices = market_df.iloc[-5]
    onemth_prices = market_df.iloc[-20]
    
    results = []
    for idx, row in portfolio_df.iterrows():
        pair = row['Currency_Pair']
        pos_type = str(row['Position_Type'])
        notional = float(row['Notional_USD'])
        entry_price = float(row['Entry_Price'])
        
        if pair not in current_prices:
            continue
            
        current_price = current_prices[pair]
        yst_price = yst_prices[pair]
        onewk_price = onewk_prices[pair]
        onemth_price = onemth_prices[pair]
        if np.isnan(current_price):
            current_price = yst_price
        
        direction = 1 if pos_type.upper() in ['BUY'] else -1
        is_usd_quote = pair.endswith('USD')
        
        if is_usd_quote:
            inception_pnl = notional * ((current_price - entry_price) / entry_price) * direction
            daily_pnl = notional * ((current_price - yst_price) / entry_price) * direction
            one_wk_pnl = notional * ((current_price - onewk_price) / entry_price) * direction
            one_mth_pnl = notional * ((current_price - onemth_price) / entry_price) * direction
        else:
            inception_pnl = notional * ((current_price - entry_price) / current_price) * direction
            daily_pnl = notional * (entry_price * (current_price - yst_price) / (current_price * yst_price)) * direction
            one_wk_pnl = notional * (entry_price * (current_price - onewk_price) / (current_price * onewk_price)) * direction
            one_mth_pnl = notional * (entry_price * (current_price - onemth_price) / (current_price * onemth_price)) * direction

        usd_exposure = notional * direction
            
        results.append({
            'Trade_ID': row['Trade_ID'],
            'Trade_Date': row['Trade_Date'],
            'Currency_Pair': pair,
            'Position_Type': pos_type,
            'Notional_USD': notional,
            'Entry_Price': entry_price,
            'Current_Price': current_price,
            'Daily_PnL_USD': daily_pnl,
            'Inception_PnL_USD': inception_pnl,
            '1Wk_PnL_USD': one_wk_pnl,
            '1Mth_PnL_USD': one_mth_pnl,
            'USD_Exposure': usd_exposure,
        })
        
    return pd.DataFrame(results)

def calculate_var_risk(analytics_df, market_df, confidence_level=0.95, holding_period=1):
    """
    Calculates Position VaR, Portfolio VaR, and Marginal/Component VaR decomposition.
    """
    if analytics_df.empty or market_df.empty:
        return 0.0, pd.DataFrame()
        
    # Compute daily logarithmic returns
    daily_returns = np.log(market_df / market_df.shift(1)).dropna()
    
    # Aggregate net USD exposure per currency pair
    pair_exposures = analytics_df.groupby('Currency_Pair')['USD_Exposure'].sum()
    active_pairs = pair_exposures.index.tolist()
    
    sub_returns = daily_returns[active_pairs]
    cov_matrix = sub_returns.cov()
    
    w = pair_exposures.values  # Exposure vector in USD
    z_score = stats.norm.ppf(confidence_level)
    scale = np.sqrt(holding_period)
    
    # Portfolio Variance & Volatility
    port_var = w.T @ cov_matrix.values @ w
    port_sd = np.sqrt(max(0, port_var))
    portfolio_var_usd = z_score * port_sd * scale
    
    # Marginal & Component VaR
    if port_sd > 0:
        marginal_var = (cov_matrix.values @ w) / port_sd * z_score * scale
        component_var = marginal_var * w
    else:
        marginal_var = np.zeros(len(w))
        component_var = np.zeros(len(w))
        
    # Standalone Position VaR
    pair_vols = sub_returns.std()
    standalone_var = np.abs(w) * pair_vols.values * z_score * scale
    
    risk_summary_df = pd.DataFrame({
        'Currency_Pair': active_pairs,
        'USD_Exposure': w,
        'Standalone_VaR_USD': standalone_var,
        'Marginal_VaR': marginal_var,
        'Component_VaR_USD': component_var,
        'Percentage_Risk_Contrib': (component_var / portfolio_var_usd * 100) if portfolio_var_usd > 0 else 0
    })
    
    return portfolio_var_usd, risk_summary_df