# Portfolio_Management_Dashboard

# FX Portfolio and Risk Management Dashboard

An interactive FX Spot portfolio management and risk monitoring dashboard built using Python and Streamlit. The application loads sample trade blotter records from a CSV file, ingests market data from yahoo finance, tracks portfolio P&L, and conducts portfolio risk analysis.

---

## Dataset Schema

Portfolio trades are sourced from a local CSV file (`portfolio.csv`) containing the following fields:

- `Trade_ID`: Unique trade transaction identifier
- `Trade_Date`: Trade execution date (`YYYY-MM-DD`)
- `Currency_Pair`: Currency ticker pair (e.g., `EURUSD`, `USDJPY`)
- `Position_Type`: Stance of the trade (`Buy` or `Sell`)
- `Notional_USD`: Trade notional value denominated in USD
- `Entry_Price`: Executed exchange rate at trade entry

---

## Key Features

### 1. Top-Level KPI Summary Cards

Prominently displayed at the top of the dashboard for high-level monitoring:

- Total Daily P&L (USD)
- Total P&L (USD)
- Total Capital Utilised (USD)
- Portfolio Value at Risk (VaR)
- Portfolio Conditional Value at Risk
- Net USD Exposure

### 2. Position P&L Page

- Position-level summary table aggregated by currency pair:
  - Net USD Exposure
  - Volume-Weighted Average Entry Price (VWAP)
  - Current Market Price
  - Multi-horizon P&L attribution: Daily, 1-Week, 1-Month, and Inception P&L (USD)
- Portfolio Performance Over Time:
  - Time series chart and data table tracking daily cumulative return and portfolio valuation
  - Key summary performance metrics: Total Return (%), Annualized Sharpe Ratio, and Maximum Drawdown (%)

### 3. Position Risk Page

Granular, position-level parametric risk analytics displayed in a summary table and risk contribution charts:

- Net USD Exposure per currency pair
- Position Value at Risk (VaR) and Conditional Value at Risk (CVaR)
- Marginal VaR and Marginal CVaR
- Component VaR and Component CVaR (Euler decomposition to aggregate portfolio risk)
- Concentration Risk visualisations by currencies: Position VaR, Component VaR, and USD exposure distributions

### 4. Trade Details Page

Blotter view broken down to the individual trade execution level:

- Complete record fields: `Trade_ID`, `Trade_Date`, `Currency_Pair`, `Position_Type`, `Notional_USD`, `Entry_Price`, and `Current_Price`
- Individual trade P&L tracking across Daily, 1-Week, 1-Month, and Inception horizons

### 5. Interactive Sidebar Controls

- **Refresh Data Button**: Clears cached market data and updates portfolio valuations with current market prices
- **Currency Filter**: Multi-select filter to view specific currency pairs
- **Date Filter**: Range selectors to filter trades by historical execution date
- **Risk Model Parameters**: Configurable Confidence Level (e.g., 90%, 95%, 99%) and Holding Period (in days) for VaR and CVaR calculations

---

## Methodology (VaR)

Risk calculations implement the Variance-Covariance (parametric) method:

- **Normal Distribution of Returns**: Daily exchange rate percentage returns are assumed to be independent, identically distributed, and follow a multivariate normal distribution.
- **Portfolio Standard Deviation**:

$$\sigma_p = \sqrt{\mathbf{w}^T \boldsymbol{\Sigma} \mathbf{w}}$$

Where $\mathbf{w}$ represents currency net exposures and $\boldsymbol{\Sigma}$ is the sample covariance matrix of returns.

- **Portfolio VaR**:

$$\text{VaR}_\alpha = z_\alpha \cdot \sigma_p \cdot \sqrt{h}$$

Where $z_\alpha$ is the critical value of the standard normal distribution and $h$ is the holding period.

- **Portfolio CVaR**:

$$\text{CVaR}_\alpha = \frac{\phi(z_\alpha)}{1 - \alpha} \cdot \sigma_p \cdot \sqrt{h}$$

Where $\phi(\cdot)$ is the standard normal probability density function.

- **Marginal and Component Risk**:
  - Marginal VaR reflects the first derivative of portfolio risk with respect to position weight:

$$\text{Marginal VaR}_i = z_\alpha \cdot \frac{(\boldsymbol{\Sigma} \mathbf{w})_i}{\sigma_p} \cdot \sqrt{h}$$

- Component VaR represents the additive dollar risk contribution:

$$\text{Component VaR}_i = w_i \cdot \text{Marginal VaR}_i, \quad \sum_{i} \text{Component VaR}_i = \text{Portfolio VaR}$$

---

## Project Assumptions

- **Normal Distribution of Returns**: FX log/percentage returns are assumed to follow a normal distribution.
- **No Cross-Currency Trades**: All currency pairs are executed directly against USD (e.g., `USDKRW`, `USDSGD`). There are no non-USD crosses (e.g., `KRWTHB`, `SGDMYR`) in the portfolio.
- **AUM**: USD100,000,000.
- **Risk-Free Rate**: Taken to be annualized 3%.

---

## Project Limitations

- **Parametric Normality Assumption**: Daily FX percentage returns are assumed to follow a normal distribution. In practice, FX markets exhibit fat tails and tail dependence during volatile periods, leading to an underestimation of extreme tail losses.
- **Absence of Non-USD Crosses**: Non-USD Crosses cannot be evaluated.
- **Exclusion of Transaction Costs**: Calculations currently exclude bid-ask execution spreads, broker brokerage fees etc.
- **Public Free Market Data Ingestion**: The system relies on free market data from Yahoo Finance, which can introduce delayed prints or gaps. These gaps are currently mitigated via forward-filling, which may temporarily mask stale price levels.

## Future Enhancements (Beyond Project Limitations)

- **Stress Testing Engine**: Add a dedicated stress testing page evaluating the portfolio under sudden exchange rate shocks and volatility spikes.
  - Historical Scenario Analysis: Simulate portfolio performance against notable market crisis events, such as:
    - 2008 Global Financial Crisis
    - 2020 COVID-19 liquidity shock

---

## Installation and Setup

### 1. Prerequisites

Python 3.11 or higher is required.

### 2. Clone Repository, Install Requirements and Run Application

```bash
git clone git@github.com:Chuacx13/Portfolio_Management_Dashboard.git
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```
