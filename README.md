# Financial Index Candlestick Chart & Signal Analysis

A Flask web application that displays candlestick charts for financial indices with technical indicators and trading signals. The application also features AI-powered market analysis using Google's Gemini.

## Features

- Interactive candlestick charts for financial indices from various exchanges
- Real-time technical analysis with multiple indicators:
  - Simple Moving Averages (SMA)
  - Relative Strength Index (RSI)
  - Moving Average Convergence Divergence (MACD)
  - Stochastic Oscillator
  - Bollinger Bands
- Customizable trading strategies with user-defined parameters
- Automated trading signal generation (CALL/PUT/HOLD)
- Live data updates from TradingView
- Integration with Google Gemini AI for advanced market analysis
- User-friendly interface with customizable parameters

## Technical Indicators & Strategies

The application uses several technical indicators that can be combined to create customized trading strategies:

- **SMA (Simple Moving Average)**: Two SMAs (short-term 20-period and long-term 50-period) to identify trends
- **RSI (Relative Strength Index)**: 14-period RSI to identify overbought or oversold conditions
- **MACD (Moving Average Convergence Divergence)**: 12/26/9 settings for trend and momentum analysis
- **Stochastic Oscillator**: Identifies potential reversal points through overbought/oversold conditions
- **Bollinger Bands**: Volatility-based indicator to identify potential price targets

### Default NIFTY 50 Strategy

The application includes an optimized default strategy for NIFTY 50 that combines MACD and RSI:

- **CALL Signal**: Generated when MACD line crosses above the signal line with positive histogram AND RSI is below 40
- **PUT Signal**: Generated when MACD line crosses below the signal line with negative histogram AND RSI is above 60
- This strategy focuses on detecting momentum changes confirmed by RSI readings

### Customizing Strategies

Users can customize their trading strategies by:
- Enabling/disabling specific indicators (SMA, MACD, Stochastic, Bollinger Bands)
- Adjusting RSI and Stochastic overbought/oversold levels
- Setting minimum signal confirmations required for CALL/PUT signals
- Accessing the strategy customization panel via the "Customize Strategy" button

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/Purv-Kabaria/Trading-Bot.git
   cd financial-chart-viewer
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your Google API key (for Gemini analysis):
   ```
   GOOGLE_API_KEY="your api key"
   ```

4. Run the application:
   ```
   python app.py
   ```

5. Open your browser and navigate to:
   ```
   http://127.0.0.1:5000/
   ```

## Usage

1. Select a common index from the dropdown or enter custom symbol and exchange
2. Specify the number of candles to retrieve (minimum 51 recommended for technical indicators)
3. Click "Get Chart & Signal" to view the candlestick chart and initial signal
4. To customize your trading strategy, click the "Customize Strategy" button
5. The application will automatically update the signal every minute
6. Click "Get Gemini Analysis" for AI-powered market insights based on current data

## Common Index and Exchange Combinations

- Nifty 50 (India): Symbol = "NIFTY", Exchange = "NSE"
- Sensex (India): Symbol = "SENSEX", Exchange = "BSE"
- Dow Jones (US): Symbol = "DJI", Exchange = "DJ"
- S&P 500 (US): Symbol = "SPX", Exchange = "SP"
- NASDAQ (US): Symbol = "IXIC", Exchange = "NASDAQ"
- FTSE 100 (UK): Symbol = "UKX", Exchange = "LSE"
- Will be adding more soon.

## Dependencies

- Flask: Web framework
- tvDatafeed: Library to fetch data from TradingView
- Plotly: Interactive chart visualization
- Pandas: Data manipulation and analysis
- Python-dotenv: Environment variable management
- Google Generative AI: For Gemini AI integration

## Note

- The application uses the tvDatafeed library to fetch historical data from TradingView
- Data availability depends on market hours and TradingView's data policies
- Gemini AI analysis requires a valid Google API key with access to Gemini services
- The default trading strategy is not made by me, use at your own risk.