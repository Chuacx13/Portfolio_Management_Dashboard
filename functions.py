import pandas as pd
import numpy as np
from scipy.stats import norm
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
    return data.ffill()

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

def calculate_pnl_by_position(analytics_df):
    if analytics_df.empty:
        return pd.DataFrame()

    df = analytics_df.copy()

    is_usd_quote = df['Currency_Pair'].str.endswith('USD')

    df['Base_Units'] = np.where(
        is_usd_quote,
        df['Notional_USD'] / df['Entry_Price'],
        df['Notional_USD']
    )
    df['Quote_Units'] = np.where(
        is_usd_quote,
        df['Notional_USD'],
        df['Notional_USD'] * df['Entry_Price']
    )

    summary = df.groupby('Currency_Pair', as_index=False).agg({
        'USD_Exposure': 'sum',          
        'Base_Units': 'sum',
        'Quote_Units': 'sum',
        'Current_Price': 'first',       
        'Daily_PnL_USD': 'sum',
        'Inception_PnL_USD': 'sum',
        '1Wk_PnL_USD': 'sum',
        '1Mth_PnL_USD': 'sum',
    }).rename(columns={'USD_Exposure': 'Net_USD_Exposure'})

    summary['Position_Type'] = np.where(
        summary['Net_USD_Exposure'] > 0, 'Buy',
        np.where(summary['Net_USD_Exposure'] < 0, 'Sell', 'Flat')
    )

    summary['Entry_Price'] = np.where(
        summary['Base_Units'] > 0,
        summary['Quote_Units'] / summary['Base_Units'],
        np.nan
    )

    cols = [
        'Currency_Pair',
        'Position_Type',
        'Net_USD_Exposure',
        'Entry_Price',
        'Current_Price',
        'Daily_PnL_USD',
        'Inception_PnL_USD',
        '1Wk_PnL_USD',
        '1Mth_PnL_USD'
    ]
    return summary[cols]

def calculate_pnl_over_time(portfolio_df, market_df, initial_portfolio_nav=100000000, rf_annual=0.03, trading_days=252):
    if portfolio_df.empty or market_df.empty:
        return None, None

    market_df = market_df.copy()
    market_df.index = pd.to_datetime(market_df.index)
    market_df.sort_index(inplace=True)

    portfolio_df = portfolio_df.copy()
    portfolio_df['Trade_Date'] = pd.to_datetime(portfolio_df['Trade_Date'])

    earliest_trade_date = portfolio_df['Trade_Date'].min()
    mkt_sub = market_df.loc[market_df.index >= earliest_trade_date]

    dates = mkt_sub.index
    trade_cum_pnl = pd.DataFrame(index=dates, columns=portfolio_df['Trade_ID'])

    for _, row in portfolio_df.iterrows():
        t_id = row['Trade_ID']
        pair = row['Currency_Pair']
        pos_type = str(row['Position_Type'])
        notional_usd = float(row['Notional_USD'])
        entry_price = float(row['Entry_Price'])
        trade_date = row['Trade_Date']

        if pair not in mkt_sub.columns:
            trade_cum_pnl[t_id] = 0.0
            continue

        prices = mkt_sub[pair]
        direction = 1 if pos_type.strip() in ['Buy'] else -1
        is_usd_quote = pair.upper().endswith('USD')

        if is_usd_quote:
            pnl_series = (
                notional_usd
                * ((prices - entry_price) / entry_price)
                * direction
            )
        else:
            pnl_series = (
                notional_usd
                * ((prices - entry_price) / prices)
                * direction
            )

        trade_cum_pnl[t_id] = pnl_series.where(dates >= trade_date, 0)

    total_cum_pnl = trade_cum_pnl.sum(axis=1)
    daily_pnl = total_cum_pnl.diff().fillna(total_cum_pnl.iloc[0])
    portfolio_nav = initial_portfolio_nav + total_cum_pnl

    daily_returns = portfolio_nav.pct_change().fillna(0.0)
    cum_return_pct = (portfolio_nav - initial_portfolio_nav) / initial_portfolio_nav * 100

    rf_daily = rf_annual / trading_days
    excess_daily_returns = daily_returns - rf_daily

    ret_std = daily_returns.std(ddof=1)
    full_sharpe = (
        (excess_daily_returns.mean() / ret_std * np.sqrt(trading_days))
        if ret_std > 0
        else 0.0
    )

    running_peak = portfolio_nav.cummax()
    drawdown_series = (portfolio_nav - running_peak) / running_peak * 100
    max_drawdown = drawdown_series.min()

    portfolio_ts = pd.DataFrame(
        {
            'Daily_PnL_USD': daily_pnl,
            'Cum_PnL_USD': total_cum_pnl,
            'Portfolio_NAV': portfolio_nav,
            'Cum_Return_Pct': cum_return_pct,
            'Drawdown_Pct': drawdown_series,
        },
        index=dates,
    )

    metrics = {
        'Total_Cum_PnL_USD': total_cum_pnl.iloc[-1],
        'Total_Return_Pct': cum_return_pct.iloc[-1],
        'Sharpe_Ratio_Ann': full_sharpe,
        'Max_Drawdown_Pct': max_drawdown,
        'Final_NAV_USD': portfolio_nav.iloc[-1],
    }

    return portfolio_ts, metrics

def calculate_var_risk(analytics_df, market_df, confidence_level=0.95, holding_period=1):
    if analytics_df.empty or market_df.empty:
        return 0.0, 0.0, pd.DataFrame()

    exposures = analytics_df.groupby('Currency_Pair')['USD_Exposure'].sum()
    pairs = [p for p in exposures.index if p in market_df.columns]
    if not pairs:
        return 0.0, 0.0, pd.DataFrame()

    w = exposures[pairs].values
    returns = market_df[pairs].pct_change().dropna()
    if returns.empty:
        return 0.0, 0.0, pd.DataFrame()

    # Covariance & portfolio volatility
    cov_matrix = returns.cov().values
    cov_w = cov_matrix @ w
    port_variance = w @ cov_w
    if port_variance <= 0:
        return 0.0, 0.0, pd.DataFrame()

    port_sigma = np.sqrt(port_variance)
    scale = np.sqrt(holding_period)

    z = norm.ppf(confidence_level)
    k = norm.pdf(z) / (1.0 - confidence_level)

    # Portfolio risk
    portfolio_var = z * port_sigma * scale
    portfolio_cvar = k * port_sigma * scale

    # Marginal & Component decompositions 
    marginal_var = z * (cov_w / port_sigma) * scale
    component_var = w * marginal_var

    marginal_cvar = k * (cov_w / port_sigma) * scale
    component_cvar = w * marginal_cvar

    # Standalone position risk
    asset_sigmas = np.sqrt(np.diag(cov_matrix))
    position_var = np.abs(w) * (z * asset_sigmas * scale)
    position_cvar = np.abs(w) * (k * asset_sigmas * scale)

    risk_summary_df = pd.DataFrame({
        'Currency_Pair': pairs,
        'USD_Net_Exposure': w,
        'VaR': position_var,
        'Marginal_VaR': marginal_var,
        'Component_VaR': component_var,
        'Pct_VaR_Contrib': component_var / portfolio_var,
        'CVaR': position_cvar,
        'Marginal_CVaR': marginal_cvar,
        'Component_CVaR': component_cvar,
        'Pct_CVaR_Contrib': component_cvar / portfolio_cvar,
    })

    return portfolio_var, portfolio_cvar, risk_summary_df