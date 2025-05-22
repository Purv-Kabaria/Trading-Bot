from flask import Flask, render_template, request, jsonify
from tvDatafeed import TvDatafeed, Interval
import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder
import json
import pandas as pd
import numpy as np
import datetime
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
tv = TvDatafeed()

DEFAULT_STRATEGY = {
    'sma_cross': False,
    'rsi_levels': True,
    'macd_signal': True,
    'stoch_signal': False,
    'bb_strategy': False,
    'rsi_oversold': 40,
    'rsi_overbought': 60,
    'stoch_oversold': 20,
    'stoch_overbought': 80,
    'min_signals_for_call': 1,
    'min_signals_for_put': 1
}

CURRENT_STRATEGY = DEFAULT_STRATEGY.copy()

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

def calc_ema(data, win):
    if data is None or not isinstance(data, pd.Series) or data.empty:
        return pd.Series(dtype=float)
    return data.ewm(span=win, adjust=False).mean()

def calc_macd(data, fast_period=12, slow_period=26, signal_period=9):
    if data is None or not isinstance(data, pd.Series) or data.empty:
        return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)
    
    ema_fast = calc_ema(data, fast_period)
    ema_slow = calc_ema(data, slow_period)
    macd_line = ema_fast - ema_slow
    signal_line = calc_ema(macd_line, signal_period)
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram

def calc_stochastic(data_high, data_low, data_close, k_period=14, d_period=3, slowing=3):
    if (data_high is None or data_low is None or data_close is None or 
        not isinstance(data_high, pd.Series) or not isinstance(data_low, pd.Series) or 
        not isinstance(data_close, pd.Series) or data_close.empty):
        return pd.Series(dtype=float), pd.Series(dtype=float)
    
    lowest_low = data_low.rolling(window=k_period).min()
    highest_high = data_high.rolling(window=k_period).max()
    
    denominator = highest_high - lowest_low
    denominator = denominator.replace(0, np.nan)
    
    k_fast = 100 * ((data_close - lowest_low) / denominator)
    k_slow = k_fast.rolling(window=slowing).mean()
    d_slow = k_slow.rolling(window=d_period).mean()
    return k_slow, d_slow

def calc_bollinger_bands(data, window=20, num_std=2):
    if data is None or not isinstance(data, pd.Series) or data.empty:
        return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)
    
    middle_band = calc_sma(data, window)
    std = data.rolling(window=window).std()
    upper_band = middle_band + (std * num_std)
    lower_band = middle_band - (std * num_std)
    return upper_band, middle_band, lower_band

def calc_atr(data_high, data_low, data_close, period=14):
    if (data_high is None or data_low is None or data_close is None or 
        not isinstance(data_high, pd.Series) or not isinstance(data_low, pd.Series) or 
        not isinstance(data_close, pd.Series) or data_close.empty):
        return pd.Series(dtype=float)
    
    prev_close = data_close.shift(1)
    tr1 = data_high - data_low
    tr2 = (data_high - prev_close).abs()
    tr3 = (data_low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    atr = tr.rolling(window=period).mean()
    return atr

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

def gen_signal(sym, exch, nbars, sma_short, sma_long, rsi_per, strategy_params=None):
    err = None
    bar = None
    sig = "Signal pending..."
    chart = None 
    data = None 

    if strategy_params is None:
        strategy_params = {
            'sma_cross': False,
            'rsi_levels': True,
            'macd_signal': True,
            'stoch_signal': False,
            'bb_strategy': False,
            'rsi_oversold': 40,
            'rsi_overbought': 60,
            'stoch_oversold': 20,
            'stoch_overbought': 80,
            'min_signals_for_call': 1,
            'min_signals_for_put': 1
        }

    try:
        n = int(nbars)
        if n <= 0:
            n = 5000 
    except:
        n = 5000 

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
            
            data['MACD'], data['MACD_signal'], data['MACD_hist'] = calc_macd(data['close'])
            data['Stoch_K'], data['Stoch_D'] = calc_stochastic(data['high'], data['low'], data['close'])
            data['BB_upper'], data['BB_middle'], data['BB_lower'] = calc_bollinger_bands(data['close'])
            data['ATR'] = calc_atr(data['high'], data['low'], data['close'])

            s_short = data['SMA_short'].iloc[-1]
            s_long = data['SMA_long'].iloc[-1]
            rsi = data['RSI'].iloc[-1]
            
            macd = data['MACD'].iloc[-1]
            macd_signal = data['MACD_signal'].iloc[-1]
            macd_hist = data['MACD_hist'].iloc[-1]
            stoch_k = data['Stoch_K'].iloc[-1]
            stoch_d = data['Stoch_D'].iloc[-1]
            bb_upper = data['BB_upper'].iloc[-1]
            bb_middle = data['BB_middle'].iloc[-1]
            bb_lower = data['BB_lower'].iloc[-1]
            atr = data['ATR'].iloc[-1]
            
            bar['sma_short'] = round(s_short, 2) if pd.notna(s_short) else 'N/A'
            bar['sma_long'] = round(s_long, 2) if pd.notna(s_long) else 'N/A'
            bar['rsi'] = round(rsi, 2) if pd.notna(rsi) else 'N/A'
            bar['macd'] = round(macd, 2) if pd.notna(macd) else 'N/A'
            bar['macd_signal'] = round(macd_signal, 2) if pd.notna(macd_signal) else 'N/A'
            bar['macd_hist'] = round(macd_hist, 2) if pd.notna(macd_hist) else 'N/A'
            bar['stoch_k'] = round(stoch_k, 2) if pd.notna(stoch_k) else 'N/A'
            bar['stoch_d'] = round(stoch_d, 2) if pd.notna(stoch_d) else 'N/A'
            bar['bb_upper'] = round(bb_upper, 2) if pd.notna(bb_upper) else 'N/A'
            bar['bb_middle'] = round(bb_middle, 2) if pd.notna(bb_middle) else 'N/A'
            bar['bb_lower'] = round(bb_lower, 2) if pd.notna(bb_lower) else 'N/A'
            bar['atr'] = round(atr, 2) if pd.notna(atr) else 'N/A'

            if pd.isna(s_short) or pd.isna(s_long) or pd.isna(rsi) or pd.isna(macd) or pd.isna(macd_signal):
                sig = "Indicator calc error"
            else:
                signals = []
                
                if strategy_params.get('macd_signal', True):
                    macd_strategy_signal = "HOLD"
                    if macd > macd_signal and macd_hist > 0:
                        if rsi < strategy_params.get('rsi_oversold', 40):
                            macd_strategy_signal = "CALL"
                    elif macd < macd_signal and macd_hist < 0:
                        if rsi > strategy_params.get('rsi_overbought', 60):
                            macd_strategy_signal = "PUT"
                    signals.append(macd_strategy_signal)
                
                if strategy_params.get('sma_cross', False):
                    sma_signal = "HOLD"
                    if s_short > s_long:
                        if strategy_params.get('rsi_levels', True) and rsi < strategy_params.get('rsi_oversold', 30):
                             sma_signal = "CALL"
                        elif not strategy_params.get('rsi_levels', True):
                             sma_signal = "CALL"
                    elif s_short < s_long:
                        if strategy_params.get('rsi_levels', True) and rsi > strategy_params.get('rsi_overbought', 70):
                            sma_signal = "PUT"
                        elif not strategy_params.get('rsi_levels', True):
                            sma_signal = "PUT"
                    signals.append(sma_signal)
                
                if strategy_params.get('stoch_signal', False):
                    stoch_strategy_signal = "HOLD"
                    if not pd.isna(stoch_k) and not pd.isna(stoch_d):
                        stoch_oversold = strategy_params.get('stoch_oversold', 20)
                        stoch_overbought = strategy_params.get('stoch_overbought', 80)
                        if stoch_k < stoch_oversold and stoch_d < stoch_oversold and stoch_k > stoch_d:
                            stoch_strategy_signal = "CALL"
                        elif stoch_k > stoch_overbought and stoch_d > stoch_overbought and stoch_k < stoch_d:
                            stoch_strategy_signal = "PUT"
                    signals.append(stoch_strategy_signal)
                
                if strategy_params.get('bb_strategy', False):
                    bb_strategy_signal = "HOLD"
                    close_price = data['close'].iloc[-1]
                    if not pd.isna(bb_lower) and close_price <= bb_lower:
                        bb_strategy_signal = "CALL"
                    elif not pd.isna(bb_upper) and close_price >= bb_upper:
                        bb_strategy_signal = "PUT"
                    signals.append(bb_strategy_signal)
                
                call_count = signals.count("CALL")
                put_count = signals.count("PUT")
                
                min_signals_call = strategy_params.get('min_signals_for_call', 1)
                min_signals_put = strategy_params.get('min_signals_for_put', 1)
                
                if call_count > put_count and call_count >= min_signals_call:
                    sig = "CALL"
                elif put_count > call_count and put_count >= min_signals_put:
                    sig = "PUT"
                else:
                    sig = "HOLD"

    except Exception as e:
        err = f"Error: {str(e)}"
        sig = "Error"
        
        bar = {
            'timestamp': 'N/A', 'open': 'N/A', 'high': 'N/A', 'low': 'N/A', 'close': 'N/A', 'volume': 'N/A',
            'sma_short': 'N/A', 'sma_long': 'N/A', 'rsi': 'N/A', 'macd': 'N/A', 'macd_signal': 'N/A', 
            'macd_hist': 'N/A', 'stoch_k': 'N/A', 'stoch_d': 'N/A', 'bb_upper': 'N/A', 'bb_middle': 'N/A', 
            'bb_lower': 'N/A', 'atr': 'N/A'
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
    
    global CURRENT_STRATEGY
    
    if request.method == 'POST':
        sym = request.form.get('symbol', def_sym).strip()
        exch = request.form.get('exchange', def_exch).strip()
        nbars = request.form.get('n_bars', def_bars).strip()
        
        data, _, err_msg, bar_data, sig_data = \
            gen_signal(sym, exch, nbars, sma_short, sma_long, rsi_per, CURRENT_STRATEGY)
        
        err = err_msg
        bar = bar_data
        sig = sig_data

        if data is not None and not data.empty:
            fig = go.Figure()
            fig.add_trace(
                go.Candlestick(
                    x=data.index,
                    open=data['open'],
                    high=data['high'],
                    low=data['low'],
                    close=data['close'],
                    increasing_line_color='green',
                    decreasing_line_color='red',
                    name='Price'
                )
            )
            
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['BB_upper'],
                    mode='lines',
                    line=dict(color='rgba(173, 216, 230, 0.7)'),
                    name='BB Upper'
                )
            )
            
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['BB_middle'],
                    mode='lines',
                    line=dict(color='rgba(173, 216, 230, 0.7)'),
                    name='BB Middle'
                )
            )
            
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['BB_lower'],
                    mode='lines',
                    line=dict(color='rgba(173, 216, 230, 0.7)'),
                    fill='tonexty',
                    fillcolor='rgba(173, 216, 230, 0.1)',
                    name='BB Lower'
                )
            )
            
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['SMA_short'],
                    mode='lines',
                    line=dict(color='rgba(255, 165, 0, 0.7)'),
                    name=f'SMA {sma_short}'
                )
            )
            
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['SMA_long'],
                    mode='lines',
                    line=dict(color='rgba(148, 0, 211, 0.7)'),
                    name=f'SMA {sma_long}'
                )
            )
            
            volume_fig = go.Figure()
            vol = data.get('volume')
            if vol is not None:
                colors = ['green' if data.iloc[i]['close'] >= data.iloc[i]['open'] else 'red' for i in range(len(data))]
                volume_fig.add_trace(
                    go.Bar(
                        x=data.index,
                        y=vol,
                        marker_color=colors,
                        name='Volume',
                        opacity=0.7
                    )
                )
                volume_fig.update_layout(
                    title="Volume",
                    height=150,
                    margin=dict(l=0, r=0, t=30, b=0)
                )
            
            macd_fig = go.Figure()
            macd_fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['MACD'],
                    mode='lines',
                    line=dict(color='blue'),
                    name='MACD Line'
                )
            )
            
            macd_fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['MACD_signal'],
                    mode='lines',
                    line=dict(color='red'),
                    name='Signal Line'
                )
            )
            
            colors = ['green' if val >= 0 else 'red' for val in data['MACD_hist']]
            macd_fig.add_trace(
                go.Bar(
                    x=data.index,
                    y=data['MACD_hist'],
                    marker_color=colors,
                    name='Histogram'
                )
            )
            macd_fig.update_layout(
                title="MACD (12,26,9)",
                height=200,
                margin=dict(l=0, r=0, t=30, b=0)
            )
            
            rsi_fig = go.Figure()
            rsi_fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['RSI'],
                    mode='lines',
                    line=dict(color='purple'),
                    name='RSI'
                )
            )
            
            rsi_fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold (30)")
            rsi_fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought (70)")
            rsi_fig.update_layout(
                title="RSI (14)",
                height=150,
                margin=dict(l=0, r=0, t=30, b=0)
            )
            
            stoch_fig = go.Figure()
            stoch_fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['Stoch_K'],
                    mode='lines',
                    line=dict(color='blue'),
                    name='%K'
                )
            )
            
            stoch_fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data['Stoch_D'],
                    mode='lines',
                    line=dict(color='red'),
                    name='%D'
                )
            )
            
            stoch_fig.add_hline(y=20, line_dash="dash", line_color="green", annotation_text="Oversold (20)")
            stoch_fig.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="Overbought (80)")
            stoch_fig.update_layout(
                title="Stochastic Oscillator",
                height=150,
                margin=dict(l=0, r=0, t=30, b=0)
            )
            
            fig.update_layout(
                title=f'{sym} - {exch} - 1 Minute Candles ({nbars} bars)',
                xaxis_title='Time',
                yaxis_title='Price',
                height=600,
                xaxis_rangeslider_visible=False,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            chart_data = {
                'main': json.loads(json.dumps(fig, cls=PlotlyJSONEncoder)),
                'volume': json.loads(json.dumps(volume_fig, cls=PlotlyJSONEncoder)),
                'macd': json.loads(json.dumps(macd_fig, cls=PlotlyJSONEncoder)),
                'rsi': json.loads(json.dumps(rsi_fig, cls=PlotlyJSONEncoder)),
                'stoch': json.loads(json.dumps(stoch_fig, cls=PlotlyJSONEncoder))
            }
            
            chart = json.dumps(chart_data)
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
    
    global CURRENT_STRATEGY

    _, _, err, bar, sig = gen_signal(sym, exch, nbars, sma_short, sma_long, rsi_per, CURRENT_STRATEGY)

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
    
    global CURRENT_STRATEGY
    
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
        
        data['MACD'], data['MACD_signal'], data['MACD_hist'] = calc_macd(data['close'])
        data['Stoch_K'], data['Stoch_D'] = calc_stochastic(data['high'], data['low'], data['close'])
        data['BB_upper'], data['BB_middle'], data['BB_lower'] = calc_bollinger_bands(data['close'])
        
        s_short = data['SMA_short'].iloc[-1]
        s_long = data['SMA_long'].iloc[-1]
        rsi = data['RSI'].iloc[-1]
        macd = data['MACD'].iloc[-1]
        macd_signal = data['MACD_signal'].iloc[-1]
        macd_hist = data['MACD_hist'].iloc[-1]
        stoch_k = data['Stoch_K'].iloc[-1]
        stoch_d = data['Stoch_D'].iloc[-1]
        bb_upper = data['BB_upper'].iloc[-1]
        bb_middle = data['BB_middle'].iloc[-1]
        bb_lower = data['BB_lower'].iloc[-1]
        
        current_signal = "Signal pending..."
        if pd.isna(s_short) or pd.isna(s_long) or pd.isna(rsi) or pd.isna(macd) or pd.isna(macd_signal):
            current_signal = "Indicator calc error"
        else:
            signals = []
            strategy_params = CURRENT_STRATEGY.copy()
                
            if strategy_params.get('macd_signal', True):
                macd_strategy_signal = "HOLD"
                if macd > macd_signal and macd_hist > 0:
                    if rsi < strategy_params.get('rsi_oversold', 40):
                        macd_strategy_signal = "CALL"
                elif macd < macd_signal and macd_hist < 0:
                    if rsi > strategy_params.get('rsi_overbought', 60):
                        macd_strategy_signal = "PUT"
                signals.append(macd_strategy_signal)
            
            if strategy_params.get('sma_cross', False):
                sma_signal = "HOLD"
                if s_short > s_long:
                    if strategy_params.get('rsi_levels', True) and rsi < strategy_params.get('rsi_oversold', 30):
                         sma_signal = "CALL"
                    elif not strategy_params.get('rsi_levels', True):
                         sma_signal = "CALL"
                elif s_short < s_long:
                    if strategy_params.get('rsi_levels', True) and rsi > strategy_params.get('rsi_overbought', 70):
                        sma_signal = "PUT"
                    elif not strategy_params.get('rsi_levels', True):
                        sma_signal = "PUT"
                signals.append(sma_signal)
            
            if strategy_params.get('stoch_signal', False):
                stoch_strategy_signal = "HOLD"
                if not pd.isna(stoch_k) and not pd.isna(stoch_d):
                    stoch_oversold = strategy_params.get('stoch_oversold', 20)
                    stoch_overbought = strategy_params.get('stoch_overbought', 80)
                    if stoch_k < stoch_oversold and stoch_d < stoch_oversold and stoch_k > stoch_d:
                        stoch_strategy_signal = "CALL"
                    elif stoch_k > stoch_overbought and stoch_d > stoch_overbought and stoch_k < stoch_d:
                        stoch_strategy_signal = "PUT"
                signals.append(stoch_strategy_signal)
            
            if strategy_params.get('bb_strategy', False):
                bb_strategy_signal = "HOLD"
                close_price = data['close'].iloc[-1]
                if not pd.isna(bb_lower) and close_price <= bb_lower:
                    bb_strategy_signal = "CALL"
                elif not pd.isna(bb_upper) and close_price >= bb_upper:
                    bb_strategy_signal = "PUT"
                signals.append(bb_strategy_signal)
            
            call_count = signals.count("CALL")
            put_count = signals.count("PUT")
            
            min_signals_call = strategy_params.get('min_signals_for_call', 1)
            min_signals_put = strategy_params.get('min_signals_for_put', 1)
            
            if call_count > put_count and call_count >= min_signals_call:
                current_signal = "CALL"
            elif put_count > call_count and put_count >= min_signals_put:
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
            'rsi': round(rsi, 2) if pd.notna(rsi) else 'N/A',
            'macd': round(macd, 2) if pd.notna(macd) else 'N/A',
            'macd_signal': round(macd_signal, 2) if pd.notna(macd_signal) else 'N/A',
            'macd_hist': round(macd_hist, 2) if pd.notna(macd_hist) else 'N/A',
            'stoch_k': round(stoch_k, 2) if pd.notna(stoch_k) else 'N/A',
            'stoch_d': round(stoch_d, 2) if pd.notna(stoch_d) else 'N/A',
            'bb_upper': round(bb_upper, 2) if pd.notna(bb_upper) else 'N/A',
            'bb_middle': round(bb_middle, 2) if pd.notna(bb_middle) else 'N/A',
            'bb_lower': round(bb_lower, 2) if pd.notna(bb_lower) else 'N/A'
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
  
  MACD Line ({data.get('macd_fast_period', 12)},{data.get('macd_slow_period', 26)}): {data.get('macd', 'N/A')}
  MACD Signal ({data.get('macd_signal_period', 9)}): {data.get('macd_signal', 'N/A')}
  
  Stochastic %K ({data.get('stoch_k_period', 14)}): {data.get('stoch_k', 'N/A')}
  Stochastic %D ({data.get('stoch_d_period', 3)}): {data.get('stoch_d', 'N/A')}
  
  Bollinger Upper Band: {data.get('bb_upper', 'N/A')}
  Bollinger Middle Band: {data.get('bb_middle', 'N/A')}
  Bollinger Lower Band: {data.get('bb_lower', 'N/A')}
-------------------------
Current Automated Signal: {data.get('signal', 'N/A')}
-------------------------
Please provide a comprehensive technical analysis for {data.get('symbol', 'this asset')}, taking into account all the indicators provided above. 

Your analysis should include:

1. Market Assessment: Current price trend and positioning in the context of recent market movements.

2. Technical Analysis:
   - Moving Averages: Interpretation of SMA Short and Long positions and potential crossovers.
   - RSI: Whether the asset is overbought/oversold and potential divergences.
   - MACD: Signal line crossovers, histogram trends, and momentum signals.
   - Stochastic Oscillator: %K and %D relationship, overbought/oversold conditions.
   - Bollinger Bands: Price position relative to bands, potential breakouts or reversals.

3. Trading Strategy Suggestions:
   - Entry and exit points based on indicator convergence/divergence.
   - Stop-loss and take-profit recommendations with reasoning.
   - Time frame considerations for the suggested strategy.

4. Risk Considerations:
   - Key levels to watch for invalidation of the analysis.
   - Market factors that could impact this technical analysis.
   - Appropriate position sizing recommendations given current volatility.

Please ensure your analysis is balanced, noting both bullish and bearish signals across different indicators.
"""

        model = genai.GenerativeModel('gemini-2.0-flash')
        resp = model.generate_content(prompt)

        return jsonify({
            "analysis": resp.text,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        })

    except Exception as e:
        return jsonify({"error": f"Failed: {str(e)}"}), 500

@app.route('/update_strategy', methods=['POST'])
def update_strategy():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data"}), 400
            
        global CURRENT_STRATEGY
        
        CURRENT_STRATEGY = {
            'sma_cross': data.get('sma_cross', False),
            'rsi_levels': data.get('rsi_levels', True),
            'macd_signal': data.get('macd_signal', True),
            'stoch_signal': data.get('stoch_signal', False),
            'bb_strategy': data.get('bb_strategy', False),
            'rsi_oversold': int(data.get('rsi_oversold', 40)),
            'rsi_overbought': int(data.get('rsi_overbought', 60)),
            'stoch_oversold': int(data.get('stoch_oversold', 20)),
            'stoch_overbought': int(data.get('stoch_overbought', 80)),
            'min_signals_for_call': int(data.get('min_signals_for_call', 1)),
            'min_signals_for_put': int(data.get('min_signals_for_put', 1))
        }
        
        return jsonify({
            "success": True,
            "message": "Strategy updated successfully",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to update strategy: {str(e)}"}), 500

@app.route('/get_strategy', methods=['GET'])
def get_strategy():
    try:
        global CURRENT_STRATEGY
        
        return jsonify({
            "success": True,
            "strategy_params": CURRENT_STRATEGY,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get strategy: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)