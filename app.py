import streamlit as st
import pandas as pd
import plotly.express as px
from functions import load_portfolio_data, fetch_market_data, calculate_pnl, calculate_var_risk
from constants import CCY

st.set_page_config(page_title='FX Portfolio Dashboard', layout='wide')

st.title('Portfolio Dashboard')

try:
    portfolio_df = load_portfolio_data('portfolio.csv')
except Exception as e:
    st.error(f'Error loading portfolio.csv: {e}')
    st.stop()

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

# Top KPI Summary Cards
total_daily_pnl = analytics_df['Daily_PnL_USD'].sum()
total_inception_pnl = analytics_df['Inception_PnL_USD'].sum()
gross_exposure = analytics_df['USD_Exposure'].abs().sum()
net_exposure = analytics_df['USD_Exposure'].sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric('Total Daily P&L (USD)', f'${total_daily_pnl:,.2f}', delta=f'{total_daily_pnl:,.2f}')
col2.metric('Total Inception P&L (USD)', f'${total_inception_pnl:,.2f}', delta=f"{total_inception_pnl:,.2f}")
col3.metric('Gross USD Exposure', f'${gross_exposure:,.2f}')
col4.metric('Net USD Exposure', f'${net_exposure:,.2f}')
    
st.markdown('---')


portfolio_var_usd, risk_summary_df = calculate_var_risk(
    analytics_df, market_df, confidence_level, holding_period
)

# Dashboard Tabs
tab1, tab2 = st.tabs(['Portfolio & P&L', 'Risk & VaR Decomposition'])

with tab1:
    st.subheader('Active Positions')

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
    
    c1, c2 = st.columns(2)
    with c1:
        fig_pnl = px.bar(
            analytics_df, x='Trade_ID', y='Inception_PnL_USD', color='Currency_Pair',
            title='Inception P&L by Trade (USD)'
        )
        st.plotly_chart(fig_pnl, use_container_width=True)
        
    with c2:
        fig_exp = px.pie(
            analytics_df, values=analytics_df['USD_Exposure'].abs(), names='Currency_Pair',
            title='USD Exposure Breakdown', hole=0.3
        )
        st.plotly_chart(fig_exp, use_container_width=True)

with tab2:
    st.subheader('Portfolio Risk Summary')
    st.metric(f'Portfolio {int(confidence_level*100)}% {holding_period}-Day Parametric VaR', f'${portfolio_var_usd:,.2f}')
    
    st.subheader('Position Risk & Component VaR Breakdown')
    st.dataframe(
        risk_summary_df.style.format({
            'USD_Exposure': '${:,.2f}',
            'Standalone_VaR_USD': '${:,.2f}',
            'Marginal_VaR': '{:.4f}',
            'Component_VaR_USD': '${:,.2f}',
            'Percentage_Risk_Contrib': '{:.2f}%'
        }),
        use_container_width=True
    )
    
    fig_comp = px.bar(
        risk_summary_df, x='Currency_Pair', y='Component_VaR_USD',
        title='Component VaR (Risk Contribution to Total Portfolio VaR)',
        color='Currency_Pair'
    )
    st.plotly_chart(fig_comp, use_container_width=True)