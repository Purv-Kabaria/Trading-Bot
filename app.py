from flask import Flask, render_template, request, jsonify
from tvDatafeed import TvDatafeed, Interval
import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder
import json
import pandas as pd
import datetime
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
tv = TvDatafeed()

API_KEY = os.environ.get("GOOGLE_API_KEY")
if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    print("WARNING: no API key")

INDICES = {
    "NIFTY": "NSE",
    "SENSEX": "BSE",
    "DJI": "DJ",
    "SPX": "SP",
    "IXIC": "NASDAQ",
    "UKX": "LSE"
}

def calc_sma(data, win):
    if data is None or not isinstance(data, pd.Series) or data.empty:
        return pd.Series(dtype=float) 
    return data.rolling(window=win).mean()

def calc_rsi(data, win=14):
    if data is None or not isinstance(data, pd.Series) or data.empty:
        return pd.Series(dtype=float) 
    
    delta = data.diff()
    
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0) 
    avg_gain = gain.rolling(window=win, min_periods=win).mean()
    avg_loss = loss.rolling(window=win, min_periods=win).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    mask1 = (avg_loss == 0) | avg_loss.isna()
    mask2 = (avg_gain == 0) | avg_gain.isna()
    rsi[mask1 & mask2] = 50.0
    rsi[mask1 & (avg_gain > 0)] = 100.0
    return rsi

def gen_signal(sym, exch, nbars, sma_short, sma_long, rsi_per):
    err = None
    bar = None
    sig = "Signal pending..."
    chart = None 
    data = None 

    try:
        n = int(nbars)
        if n <= 0:
            n = 5000 
    except:
        n = 5000 

    req_len = max(sma_long, rsi_per + 1, 1) 

    try:
        data = tv.get_hist(symbol=sym, exchange=exch, interval=Interval.in_1_minute, n_bars=n)

        if data is None or data.empty:
            err = f"No data for {sym} on {exch}."
            sig = "Data unavailable"
        else:
            data['close'] = pd.to_numeric(data['close'], errors='coerce')
            data.dropna(subset=['close'], inplace=True)

            last = data.iloc[-1]
            bar = {
                'timestamp': last.name.strftime('%Y-%m-%d %H:%M:%S'),
                'open': round(last['open'], 2),
                'high': round(last['high'], 2),
                'low': round(last['low'], 2),
                'close': round(last['close'], 2),
                'volume': int(last.get('volume', 0)) if 'volume' in last and pd.notna(last['volume']) else 'N/A'
            }

            data['SMA_short'] = calc_sma(data['close'], sma_short)
            data['SMA_long'] = calc_sma(data['close'], sma_long)
            data['RSI'] = calc_rsi(data['close'], rsi_per)

            s_short = data['SMA_short'].iloc[-1]
            s_long = data['SMA_long'].iloc[-1]
            rsi = data['RSI'].iloc[-1]
            
            bar['sma_short'] = round(s_short, 2) if pd.notna(s_short) else 'N/A'
            bar['sma_long'] = round(s_long, 2) if pd.notna(s_long) else 'N/A'
            bar['rsi'] = round(rsi, 2) if pd.notna(rsi) else 'N/A'

            if pd.isna(s_short) or pd.isna(s_long) or pd.isna(rsi):
                sig = "Indicator calc error"
            else:
                if s_short > s_long and rsi < 30:
                    sig = "CALL"
                elif s_short < s_long and rsi > 70:
                    sig = "PUT"
                else:
                    sig = "HOLD"

    except Exception as e:
        err = f"Error: {str(e)}"
        sig = "Error"
        
        bar = {
            'timestamp': 'N/A', 'open': 'N/A', 'high': 'N/A', 'low': 'N/A', 'close': 'N/A', 'volume': 'N/A',
            'sma_short': 'N/A', 'sma_long': 'N/A', 'rsi': 'N/A' 
        }
    return data, chart, err, bar, sig


@app.route('/', methods=['GET', 'POST'])
def index():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    def_sym = "NIFTY"
    def_exch = "NSE"
    def_bars = "5000" 

    chart = None
    err = None
    bar = None
    sig = "Signal pending..."
    
    sym = def_sym
    exch = def_exch
    nbars = def_bars

    sma_short = 20
    sma_long = 50
    rsi_per = 14
    
    if request.method == 'POST':
        sym = request.form.get('symbol', def_sym).strip()
        exch = request.form.get('exchange', def_exch).strip()
        nbars = request.form.get('n_bars', def_bars).strip()
        
        data, _, err_msg, bar_data, sig_data = \
            gen_signal(sym, exch, nbars, sma_short, sma_long, rsi_per)
        
        err = err_msg
        bar = bar_data
        sig = sig_data

        if data is not None and not data.empty:
            fig = go.Figure(data=[go.Candlestick(
                x=data.index,
                open=data['open'],
                high=data['high'],
                low=data['low'],
                close=data['close'],
                increasing_line_color='green',
                decreasing_line_color='red'
            )])
            
            vol = data.get('volume')
            if vol is not None:
                fig.add_trace(go.Bar(
                    x=data.index,
                    y=vol,
                    name='Volume',
                    marker_color='rgba(0, 0, 255, 0.3)',
                    yaxis="y2"
                ))
            
            fig.update_layout(
                title=f'{sym} - {exch} - 1 Minute Candles ({nbars} bars)',
                xaxis_title='Time',
                yaxis_title='Price',
                xaxis_rangeslider_visible=False,
                height=600,
                yaxis2=dict(title="Volume", overlaying="y", side="right", showgrid=False),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            chart = json.dumps(fig, cls=PlotlyJSONEncoder)
        
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            
    return render_template('index.html', current_time=now, chart_json=chart, error=err, symbol=sym, exchange=exch, n_bars=nbars, common_indices=INDICES, latest_bar=bar, trading_signal=sig)

@app.route('/get_updated_signal', methods=['GET'])
def get_signal():
    sym = request.args.get('symbol', 'NIFTY').strip()
    exch = request.args.get('exchange', 'NSE').strip()
    nbars = request.args.get('n_bars', '5000').strip()
    
    sma_short = 20
    sma_long = 50
    rsi_per = 14

    _, _, err, bar, sig = \
        gen_signal(sym, exch, nbars, sma_short, sma_long, rsi_per)

    return jsonify({
        'trading_signal': sig,
        'latest_bar': bar,
        'error_message': err,
        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    })

@app.route('/get_current_bar', methods=['GET'])
def get_current_bar():
    sym = request.args.get('symbol', 'NIFTY').strip()
    exch = request.args.get('exchange', 'NSE').strip()
    
    try:
        data = tv.get_hist(symbol=sym, exchange=exch, interval=Interval.in_1_minute, n_bars=60)
        if data is None or data.empty:
            return jsonify({
                'error_message': f"No data for {sym} on {exch}.",
                'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            })
        
        now = datetime.datetime.now()
        current_minute_start = now.replace(second=0, microsecond=0)
        last_bar = data.iloc[-1]
        
        sma_short_period = 20
        sma_long_period = 50
        rsi_period = 14
        
        data['SMA_short'] = calc_sma(data['close'], sma_short_period)
        data['SMA_long'] = calc_sma(data['close'], sma_long_period)
        data['RSI'] = calc_rsi(data['close'], rsi_period)
        
        s_short = data['SMA_short'].iloc[-1]
        s_long = data['SMA_long'].iloc[-1]
        rsi = data['RSI'].iloc[-1]
        
        current_signal = "Signal pending..."
        if pd.isna(s_short) or pd.isna(s_long) or pd.isna(rsi):
            current_signal = "Indicator calc error"
        else:
            if s_short > s_long and rsi < 30:
                current_signal = "CALL"
            elif s_short < s_long and rsi > 70:
                current_signal = "PUT"
            else:
                current_signal = "HOLD"
        
        current_bar = {
            'timestamp': current_minute_start.strftime('%Y-%m-%d %H:%M:%S'),
            'open': round(last_bar['open'], 2),
            'high': round(last_bar['high'], 2),
            'low': round(last_bar['low'], 2),
            'close': round(last_bar['close'], 2),
            'volume': int(last_bar.get('volume', 0)) if 'volume' in last_bar and pd.notna(last_bar['volume']) else 'N/A',
            'sma_short': round(s_short, 2) if pd.notna(s_short) else 'N/A',
            'sma_long': round(s_long, 2) if pd.notna(s_long) else 'N/A',
            'rsi': round(rsi, 2) if pd.notna(rsi) else 'N/A'
        }
        
        return jsonify({
            'current_bar': current_bar,
            'trading_signal': current_signal,
            'timestamp': now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        })
        
    except Exception as e:
        return jsonify({
            'error_message': f"Error: {str(e)}",
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        })

@app.route('/query_gemini', methods=['POST'])
def query_gemini():
    try:
        if not API_KEY:
            return jsonify({"error": "No API key"}), 500
        
        data = request.json
        if not data:
            return jsonify({"error": "No data"}), 400

        prompt = f"""Gemini Analysis Request:
-------------------------
Timestamp: {data.get('timestamp', 'N/A')}
Symbol: {data.get('symbol', 'N/A')}
Exchange: {data.get('exchange', 'N/A')}
Candles Used for Indicators: {data.get('n_bars', 'N/A')}
-------------------------
Latest Candle Data:
  Open: {data.get('open', 'N/A')}
  High: {data.get('high', 'N/A')}
  Low: {data.get('low', 'N/A')}
  Close: {data.get('close', 'N/A')}
  Volume: {data.get('volume', 'N/A')}
-------------------------
Technical Indicators:
  SMA Short ({data.get('sma_short_period', 20)}): {data.get('sma_short', 'N/A')}
  SMA Long ({data.get('sma_long_period', 50)}): {data.get('sma_long', 'N/A')}
  RSI ({data.get('rsi_period', 14)}): {data.get('rsi', 'N/A')}
-------------------------
Current Automated Signal: {data.get('signal', 'N/A')}
-------------------------
Please analyze this data, considering recent price action and indicator levels. What is your assessment of the current market situation for {data.get('symbol', 'this asset')}? What potential trading strategies or considerations would you highlight based on this snapshot? 
Provide your analysis with clear sections for: Market Assessment, Technical Analysis, Trading Strategy Suggestions, and Risk Considerations.
"""

        model = genai.GenerativeModel('gemini-2.0-flash')
        resp = model.generate_content(prompt)

        return jsonify({
            "analysis": resp.text,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        })

    except Exception as e:
        return jsonify({"error": f"Failed: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)