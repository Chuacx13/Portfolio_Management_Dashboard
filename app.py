import streamlit as st
import pandas as pd
import plotly.express as px
from functions import load_portfolio_data, fetch_market_data, calculate_pnl, calculate_pnl_by_position, calculate_pnl_over_time, calculate_var_risk
from constants import CCY

st.set_page_config(page_title='FX Portfolio Dashboard', layout='wide')

st.title('Portfolio Dashboard')

try:
    portfolio_df = load_portfolio_data('portfolio.csv')
except Exception as e:
    st.error(f'Error loading portfolio.csv: {e}')
    st.stop()

# Refresh Prices Button
if st.sidebar.button('Refresh Data', use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# Portfolio Filters
st.sidebar.header('Portfolio Filters')

# Filter: Currency Pair
selected_pairs = st.sidebar.multiselect('Currency Pairs', options=CCY, default=CCY)

# Filter: Date Range
min_date = portfolio_df['Trade_Date'].min().date()
max_date = portfolio_df['Trade_Date'].max().date()
start_date = st.sidebar.date_input('Start Date', value=min_date)
end_date = st.sidebar.date_input('End Date', value=max_date)

filtered_df = portfolio_df[
    (portfolio_df['Currency_Pair'].isin(selected_pairs)) &
    (portfolio_df['Trade_Date'].dt.date >= start_date) &
    (portfolio_df['Trade_Date'].dt.date <= end_date)
].copy()

if filtered_df.empty:
    st.warning('No trades match the selected filters.')
    st.stop()

st.sidebar.markdown('---')

# Risk Settings
st.sidebar.header('Risk Settings')
confidence_level = st.sidebar.select_slider('VaR Confidence Level', options=[0.90, 0.95, 0.99], value=0.95)
holding_period = st.sidebar.number_input('Holding Period (Days)', min_value=1, max_value=30, value=1)

market_df = fetch_market_data()

if market_df.empty:
    st.error('Unable to fetch market data from Yahoo Finance.')
    st.stop()

analytics_df = calculate_pnl(filtered_df, market_df)

analytics_by_position_df = calculate_pnl_by_position(analytics_df)

portfolio_var, portfolio_cvar, risk_summary_df = calculate_var_risk(
    analytics_df, market_df, confidence_level, holding_period
)

portfolio_ts, metrics = calculate_pnl_over_time(portfolio_df, market_df)

# Top KPI Summary Cards
total_daily_pnl = analytics_df['Daily_PnL_USD'].sum()
total_pnl = analytics_df['Inception_PnL_USD'].sum()
total_cap_utilised = analytics_df['USD_Exposure'].abs().sum()
net_exposure = analytics_df['USD_Exposure'].sum()

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric('Total Daily P&L (USD)', f'${total_daily_pnl:,.2f}', delta=f'{total_daily_pnl:,.2f}')
col2.metric('Total P&L (USD)', f'${total_pnl:,.2f}', delta=f"{total_pnl:,.2f}")
col3.metric('Total Capital Utilised (USD)', f'${total_cap_utilised:,.2f}')
col4.metric(
    f'Portfolio {int(confidence_level * 100)}% {holding_period}-Day VaR (USD)',
    f'${portfolio_var:,.2f}'
)
col5.metric(
    f'Portfolio {int(confidence_level * 100)}% {holding_period}-Day CVaR (USD)',
    f'${portfolio_cvar:,.2f}'
)
col6.metric('Net USD Exposure', f'${net_exposure:,.2f}')

st.markdown('---')

# Standardize color mapping for each ccy
sorted_pairs = sorted(CCY)
extended_palette = (
    px.colors.qualitative.Dark24
    + px.colors.qualitative.Light24
    + px.colors.qualitative.Alphabet
)
color_map = {pair: extended_palette[i % len(extended_palette)] for i, pair in enumerate(sorted_pairs)}

# Dashboard Tabs
tab1, tab2, tab3 = st.tabs(['Position P&L', 'Position Risk', 'Trade Details'])

with tab1:
    st.subheader('Position P&L Summary')
    display_df = analytics_by_position_df[[
        'Currency_Pair', 'Position_Type', 'Net_USD_Exposure',
        'Entry_Price', 'Current_Price', 'Inception_PnL_USD', 'Daily_PnL_USD',
        '1Wk_PnL_USD', '1Mth_PnL_USD'
    ]].copy()
    
    st.dataframe(
        display_df.style.format({
            'Net_USD_Exposure': '${:,.2f}',
            'Entry_Price': '{:.4f}',
            'Current_Price': '{:.4f}',
            'Daily_PnL_USD': '${:,.2f}',
            'Inception_PnL_USD': '${:,.2f}',
            '1Wk_PnL_USD': '${:,.2f}',
            '1Mth_PnL_USD': '${:,.2f}'
        }),
        use_container_width=True
    )

    st.subheader('Portfolio Performance Over Time')

    col1, col2, col3 = st.columns(3)
    col1.metric('Total Return', f"{metrics['Total_Return_Pct']:+.2f}%")
    col2.metric('Sharpe Ratio', f"{metrics['Sharpe_Ratio_Ann']:.2f}")
    col3.metric('Max Drawdown', f"{metrics['Max_Drawdown_Pct']:.2f}%")

    st.line_chart(portfolio_ts[['Cum_Return_Pct']])

    st.dataframe(
        portfolio_ts[
            [
                'Daily_PnL_USD',
                'Cum_PnL_USD',
                'Portfolio_NAV',
                'Cum_Return_Pct',
                'Drawdown_Pct',
            ]
        ].style.format(
            {
                'Daily_PnL_USD': '${:,.2f}',
                'Cum_PnL_USD': '${:,.2f}',
                'Portfolio_NAV': '${:,.2f}',
                'Cum_Return_Pct': '{:+.2f}%',
                'Drawdown_Pct': '{:.2f}%',
            }
        ),
        use_container_width=True,
    )
    
with tab2:
    st.subheader('Position Risk Summary')
    st.dataframe(
        risk_summary_df.style.format({
            'USD_Net_Exposure': '${:,.2f}',
            'VaR': '${:,.2f}',
            'CVaR': '${:,.2f}',
            'Marginal_VaR': '{:,.4f}',
            'Marginal_CVaR': '{:,.4f}',
            'Component_VaR': '${:,.2f}',
            'Component_CVaR': '${:,.2f}',
        }, na_rep='-'),
        use_container_width=True
    )

    pie1, pie2 = st.columns(2)
    with pie1:
        fig_var = px.pie(
            risk_summary_df, 
            values=risk_summary_df['VaR'].clip(lower=0), 
            names='Currency_Pair',
            color='Currency_Pair',                  
            color_discrete_map=color_map,
            title='Position VaR by Currency',
            hole=0.3
        )
        st.plotly_chart(fig_var, use_container_width=True)

    with pie2:
        fig_comp_var = px.pie(
            risk_summary_df, 
            values=risk_summary_df['Component_VaR'].clip(lower=0), 
            names='Currency_Pair',
            color='Currency_Pair',                  
            color_discrete_map=color_map,
            title='Component VaR by Currency',
            hole=0.3
        )
        st.plotly_chart(fig_comp_var, use_container_width=True)

    fig_usd_exp = px.pie(
        analytics_df, 
        values=analytics_df['USD_Exposure'].abs(), 
        names='Currency_Pair',
        color='Currency_Pair',                  
        color_discrete_map=color_map,
        title='USD Exposure by Currency', 
        hole=0.3
    )
    st.plotly_chart(fig_usd_exp, use_container_width=True)
    
with tab3:
    st.subheader('Trade Details')

    display_df = analytics_df[[
        'Trade_ID', 'Trade_Date', 'Currency_Pair', 'Position_Type', 'Notional_USD',
        'Entry_Price', 'Current_Price', 'Inception_PnL_USD', 'Daily_PnL_USD',
        '1Wk_PnL_USD', '1Mth_PnL_USD'
    ]].copy()
    display_df['Trade_Date'] = display_df['Trade_Date'].dt.strftime('%Y-%m-%d')
    
    st.dataframe(
        display_df.style.format({
            'Notional_USD': '{:,.0f}',
            'Entry_Price': '{:.4f}',
            'Current_Price': '{:.4f}',
            'Daily_PnL_USD': '${:,.2f}',
            'Inception_PnL_USD': '${:,.2f}',
            '1Wk_PnL_USD': '${:,.2f}',
            '1Mth_PnL_USD': '${:,.2f}'
        }),
        use_container_width=True
    )