document.addEventListener('DOMContentLoaded', (e) => {
    setupIdxHndlr();
    if (chkInitialFtch())
        updLvSig();

    setupMinuteBasedUpdates();
    setupCurrentBarUpdates();
    setInterval(updateServerTime, 1000);
    setupGemModal();
    setupStrategyModal();
    setupIndicatorToggles();
    initCharts();
});

function setupIdxHndlr() {
    const idxSel = document.getElementById('idx_sel');
    const symIn = document.getElementById('sym');
    const exchIn = document.getElementById('exch');

    if (idxSel) {
        idxSel.addEventListener('change', function () {
            const selVal = this.value;
            if (selVal) {
                const parts = selVal.split('_');
                symIn.value = parts[0];
                exchIn.value = parts[1];
            }
        });
    }
}

function chkInitialFtch() {
    const formSub = document.getElementById('chart').querySelector('script') !== null;
    const symNotDef = document.getElementById('sym') && document.getElementById('sym').value !== 'NIFTY';
    return formSub || symNotDef;
}

function updLvSig() {
    const symIn = document.getElementById('sym');
    const exchIn = document.getElementById('exch');
    const nBarsEl = document.getElementById('n_bars');

    let curSym = symIn && symIn.value ? symIn.value : 'NIFTY';
    let curExch = exchIn && exchIn.value ? exchIn.value : 'NSE';
    let curNBars = nBarsEl && nBarsEl.value ? nBarsEl.value : '5000';

    fetch(`/get_updated_signal?symbol=${encodeURIComponent(curSym)}&exchange=${encodeURIComponent(curExch)}&n_bars=${encodeURIComponent(curNBars)}`)
        .then(res => res.json())
        .then(data => {
            updUIWithLvData(data);
        });
}

function updUIWithLvData(data) {
    const lvSigEl = document.getElementById('live-sig');
    lvSigEl.textContent = data.trading_signal || 'Error';

    lvSigEl.className = 'signal';
    if (data.trading_signal)
        lvSigEl.classList.add(`signal-${data.trading_signal}`);

    document.getElementById('live-ts').textContent = data.timestamp || 'N/A';

    const lvErrEl = document.getElementById('live-err');
    if (data.error_message)
        lvErrEl.textContent = data.error_message;
    else
        lvErrEl.textContent = '';

    if (data.latest_bar) {
        document.getElementById('live-o').textContent = data.latest_bar.open ?? 'N/A';
        document.getElementById('live-h').textContent = data.latest_bar.high ?? 'N/A';
        document.getElementById('live-l').textContent = data.latest_bar.low ?? 'N/A';
        document.getElementById('live-c').textContent = data.latest_bar.close ?? 'N/A';
        document.getElementById('live-v').textContent = data.latest_bar.volume ?? 'N/A';
        document.getElementById('live-sma-s').textContent = data.latest_bar.sma_short ?? 'N/A';
        document.getElementById('live-sma-l').textContent = data.latest_bar.sma_long ?? 'N/A';
        document.getElementById('live-rsi').textContent = data.latest_bar.rsi ?? 'N/A';

        document.getElementById('live-macd').textContent = data.latest_bar.macd ?? 'N/A';
        document.getElementById('live-macd-signal').textContent = data.latest_bar.macd_signal ?? 'N/A';
        document.getElementById('live-macd-hist').textContent = data.latest_bar.macd_hist ?? 'N/A';
        document.getElementById('live-stoch-k').textContent = data.latest_bar.stoch_k ?? 'N/A';
        document.getElementById('live-stoch-d').textContent = data.latest_bar.stoch_d ?? 'N/A';
        document.getElementById('live-bb-upper').textContent = data.latest_bar.bb_upper ?? 'N/A';
        document.getElementById('live-bb-middle').textContent = data.latest_bar.bb_middle ?? 'N/A';
        document.getElementById('live-bb-lower').textContent = data.latest_bar.bb_lower ?? 'N/A';
    } else {
        document.getElementById('live-o').textContent = 'N/A';
        document.getElementById('live-h').textContent = 'N/A';
        document.getElementById('live-l').textContent = 'N/A';
        document.getElementById('live-c').textContent = 'N/A';
        document.getElementById('live-v').textContent = 'N/A';
        document.getElementById('live-sma-s').textContent = 'N/A';
        document.getElementById('live-sma-l').textContent = 'N/A';
        document.getElementById('live-rsi').textContent = 'N/A';

        document.getElementById('live-macd').textContent = 'N/A';
        document.getElementById('live-macd-signal').textContent = 'N/A';
        document.getElementById('live-macd-hist').textContent = 'N/A';
        document.getElementById('live-stoch-k').textContent = 'N/A';
        document.getElementById('live-stoch-d').textContent = 'N/A';
        document.getElementById('live-bb-upper').textContent = 'N/A';
        document.getElementById('live-bb-middle').textContent = 'N/A';
        document.getElementById('live-bb-lower').textContent = 'N/A';
    }
}

function setupGemModal() {
    const gModal = document.getElementById('gemModal');
    const prepGemBtn = document.getElementById('gemBtn');
    const closeGemBtn = document.getElementById('closeGemModal');
    const closeGemBtn2 = document.getElementById('closeGemModal2');
    const closeGemErrBtn = document.getElementById('closeGemErrBtn');
    const cpyGemBtn = document.getElementById('copyGemBtn');
    const gemOut = document.getElementById('gemOut');

    if (prepGemBtn) {
        prepGemBtn.addEventListener('click', function () {
            reqGemAna();
        });
    }

    setupModalClose(gModal, closeGemBtn, closeGemBtn2, closeGemErrBtn);
    setupCopy(cpyGemBtn, gemOut);
}

function reqGemAna() {
    const gModal = document.getElementById('gemModal');
    const reqData = gthrDataForGemAna();

    if (gModal) {
        document.getElementById('gemLoad').style.display = 'block';
        document.getElementById('gemAna').style.display = 'none';
        document.getElementById('gemErr').style.display = 'none';
        gModal.style.display = 'block';
    }

    fetch('/query_gemini', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(reqData)
    })
        .then(res => res.json())
        .then(data => {
            document.getElementById('gemLoad').style.display = 'none';
            document.getElementById('gemAna').style.display = 'block';
            document.getElementById('gemAnaTime').textContent = data.timestamp;
            document.getElementById('gemOut').value = data.analysis;
        })
        .catch(error => {
            document.getElementById('gemLoad').style.display = 'none';
            document.getElementById('gemErr').style.display = 'block';
            document.getElementById('gemErrTxt').textContent = `Error: ${error.message}`;
        });
}

function gthrDataForGemAna() {
    const curSym = document.getElementById('sym') ? document.getElementById('sym').value : 'N/A';
    const curExch = document.getElementById('exch') ? document.getElementById('exch').value : 'N/A';
    const curNBars = document.getElementById('n_bars') ? document.getElementById('n_bars').value : 'N/A';

    const lvTs = document.getElementById('live-ts') ? document.getElementById('live-ts').textContent : 'N/A';
    const lvO = document.getElementById('live-o') ? document.getElementById('live-o').textContent : 'N/A';
    const lvH = document.getElementById('live-h') ? document.getElementById('live-h').textContent : 'N/A';
    const lvL = document.getElementById('live-l') ? document.getElementById('live-l').textContent : 'N/A';
    const lvC = document.getElementById('live-c') ? document.getElementById('live-c').textContent : 'N/A';
    const lvV = document.getElementById('live-v') ? document.getElementById('live-v').textContent : 'N/A';
    const lvSmaS = document.getElementById('live-sma-s') ? document.getElementById('live-sma-s').textContent : 'N/A';
    const lvSmaL = document.getElementById('live-sma-l') ? document.getElementById('live-sma-l').textContent : 'N/A';
    const lvRsi = document.getElementById('live-rsi') ? document.getElementById('live-rsi').textContent : 'N/A';
    const lvSig = document.getElementById('live-sig') ? document.getElementById('live-sig').textContent : 'N/A';

    const lvMacd = document.getElementById('live-macd') ? document.getElementById('live-macd').textContent : 'N/A';
    const lvMacdSig = document.getElementById('live-macd-signal') ? document.getElementById('live-macd-signal').textContent : 'N/A';
    const lvStochK = document.getElementById('live-stoch-k') ? document.getElementById('live-stoch-k').textContent : 'N/A';
    const lvStochD = document.getElementById('live-stoch-d') ? document.getElementById('live-stoch-d').textContent : 'N/A';
    const lvBBUpper = document.getElementById('live-bb-upper') ? document.getElementById('live-bb-upper').textContent : 'N/A';
    const lvBBMiddle = document.getElementById('live-bb-middle') ? document.getElementById('live-bb-middle').textContent : 'N/A';
    const lvBBLower = document.getElementById('live-bb-lower') ? document.getElementById('live-bb-lower').textContent : 'N/A';

    const smaSPer = 20;
    const smaLPer = 50;
    const rsiPer = 14;
    const macdFast = 12;
    const macdSlow = 26;
    const macdSignal = 9;
    const stochK = 14;
    const stochD = 3;

    return {
        timestamp: lvTs,
        symbol: curSym,
        exchange: curExch,
        n_bars: curNBars,
        open: lvO,
        high: lvH,
        low: lvL,
        close: lvC,
        volume: lvV,
        sma_short: lvSmaS,
        sma_long: lvSmaL,
        rsi: lvRsi,
        macd: lvMacd,
        macd_signal: lvMacdSig,
        stoch_k: lvStochK,
        stoch_d: lvStochD,
        bb_upper: lvBBUpper,
        bb_middle: lvBBMiddle,
        bb_lower: lvBBLower,
        signal: lvSig,
        sma_short_period: smaSPer,
        sma_long_period: smaLPer,
        rsi_period: rsiPer,
        macd_fast_period: macdFast,
        macd_slow_period: macdSlow,
        macd_signal_period: macdSignal,
        stoch_k_period: stochK,
        stoch_d_period: stochD
    };
}

function setupModalClose(modal, ...closeBtns) {
    closeBtns.forEach(btn => {
        if (btn) {
            btn.onclick = function () {
                if (modal) modal.style.display = "none";
            }
        }
    });
}

function setupCopy(cpyBtn, txtEl) {
    if (cpyBtn && txtEl) {
        cpyBtn.addEventListener('click', function () {
            txtEl.select();
            txtEl.setSelectionRange(0, 99999);
            navigator.clipboard.writeText(txtEl.value);
            alert('Analysis copied!');
        });
    }
}

function updateServerTime() {
    const serverTimeElement = document.querySelector('.container > p:first-of-type');
    if (serverTimeElement) {
        const now = new Date();
        const options = {
            timeZone: 'Asia/Kolkata',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false,
            fractionalSecondDigits: 3
        };

        const formatter = new Intl.DateTimeFormat('en-IN', options);
        const parts = formatter.formatToParts(now);

        let formattedDate = '';
        const partValues = {};

        parts.forEach(part => {
            partValues[part.type] = part.value;
        });

        formattedDate = `${partValues.year}-${partValues.month}-${partValues.day} ${partValues.hour}:${partValues.minute}:${partValues.second}.${partValues.fractionalSecond || '000'}`;

        serverTimeElement.textContent = `Current Server Time (IST): ${formattedDate}`;
    }
}

function setupMinuteBasedUpdates() {
    updLvSig();
    const now = new Date();
    const msUntilNextMinute = (60 - now.getSeconds()) * 1000 - now.getMilliseconds();

    setTimeout(() => {
        updLvSig();
        setInterval(updLvSig, 60000);
    }, msUntilNextMinute + 1000);
}

function updateCurrentBar() {
    const symIn = document.getElementById('sym');
    const exchIn = document.getElementById('exch');

    let curSym = symIn && symIn.value ? symIn.value : 'NIFTY';
    let curExch = exchIn && exchIn.value ? exchIn.value : 'NSE';

    fetch(`/get_current_bar?symbol=${encodeURIComponent(curSym)}&exchange=${encodeURIComponent(curExch)}`)
        .then(res => res.json())
        .then(data => {
            document.getElementById('realtime-ts').textContent = data.timestamp || 'N/A';

            const curSigEl = document.getElementById('current-sig');
            if (curSigEl) {
                curSigEl.textContent = data.trading_signal || 'Unknown';
                curSigEl.className = 'signal';
                if (data.trading_signal) {
                    curSigEl.classList.add(`signal-${data.trading_signal}`);
                }
            }

            const curErrEl = document.getElementById('current-err');
            if (data.error_message) {
                curErrEl.textContent = data.error_message;
            } else {
                curErrEl.textContent = '';
            }

            if (data.current_bar) {
                document.getElementById('current-o').textContent = data.current_bar.open ?? 'N/A';
                document.getElementById('current-h').textContent = data.current_bar.high ?? 'N/A';
                document.getElementById('current-l').textContent = data.current_bar.low ?? 'N/A';
                document.getElementById('current-c').textContent = data.current_bar.close ?? 'N/A';
                document.getElementById('current-v').textContent = data.current_bar.volume ?? 'N/A';
                document.getElementById('current-sma-s').textContent = data.current_bar.sma_short ?? 'N/A';
                document.getElementById('current-sma-l').textContent = data.current_bar.sma_long ?? 'N/A';
                document.getElementById('current-rsi').textContent = data.current_bar.rsi ?? 'N/A';

                document.getElementById('current-macd').textContent = data.current_bar.macd ?? 'N/A';
                document.getElementById('current-macd-signal').textContent = data.current_bar.macd_signal ?? 'N/A';
                document.getElementById('current-macd-hist').textContent = data.current_bar.macd_hist ?? 'N/A';
                document.getElementById('current-stoch-k').textContent = data.current_bar.stoch_k ?? 'N/A';
                document.getElementById('current-stoch-d').textContent = data.current_bar.stoch_d ?? 'N/A';
                document.getElementById('current-bb-upper').textContent = data.current_bar.bb_upper ?? 'N/A';
                document.getElementById('current-bb-middle').textContent = data.current_bar.bb_middle ?? 'N/A';
                document.getElementById('current-bb-lower').textContent = data.current_bar.bb_lower ?? 'N/A';
            } else {
                document.getElementById('current-o').textContent = 'N/A';
                document.getElementById('current-h').textContent = 'N/A';
                document.getElementById('current-l').textContent = 'N/A';
                document.getElementById('current-c').textContent = 'N/A';
                document.getElementById('current-v').textContent = 'N/A';
                document.getElementById('current-sma-s').textContent = 'N/A';
                document.getElementById('current-sma-l').textContent = 'N/A';
                document.getElementById('current-rsi').textContent = 'N/A';

                document.getElementById('current-macd').textContent = 'N/A';
                document.getElementById('current-macd-signal').textContent = 'N/A';
                document.getElementById('current-macd-hist').textContent = 'N/A';
                document.getElementById('current-stoch-k').textContent = 'N/A';
                document.getElementById('current-stoch-d').textContent = 'N/A';
                document.getElementById('current-bb-upper').textContent = 'N/A';
                document.getElementById('current-bb-middle').textContent = 'N/A';
                document.getElementById('current-bb-lower').textContent = 'N/A';
            }
        })
        .catch(error => {
            document.getElementById('current-err').textContent = `Error: ${error.message}`;
        });
}

function setupCurrentBarUpdates() {
    updateCurrentBar();
    setInterval(updateCurrentBar, 3000);
}

function setupIndicatorToggles() {
    const toggleButtons = document.querySelectorAll('.indicator-toggle');

    if (toggleButtons) {
        toggleButtons.forEach(button => {
            button.addEventListener('click', function () {
                const targetId = this.getAttribute('data-target');
                const targetChart = document.getElementById(targetId);

                if (targetChart) {
                    if (targetChart.style.display === 'none') {
                        targetChart.style.display = 'block';
                        this.classList.add('active');
                    } else {
                        targetChart.style.display = 'none';
                        this.classList.remove('active');
                    }
                }
            });
        });
    }
}

function initCharts() {
    const chartContainer = document.getElementById('chart');
    if (!chartContainer) return;

    const chartDataElement = document.getElementById('chart-data');
    if (!chartDataElement) return;

    try {
        if (typeof Plotly !== 'undefined') {
            const chartData = JSON.parse(chartDataElement.textContent);
            if (!chartData)
                return;

            Plotly.newPlot('chart', chartData.main.data, chartData.main.layout);
            const indicators = document.createElement('div');
            indicators.className = 'indicators-container';
            document.getElementById('chart').appendChild(indicators);

            const volumeDiv = document.createElement('div');
            volumeDiv.id = 'volume-chart';
            indicators.appendChild(volumeDiv);
            Plotly.newPlot('volume-chart', chartData.volume.data, chartData.volume.layout);

            const macdDiv = document.createElement('div');
            macdDiv.id = 'macd-chart';
            indicators.appendChild(macdDiv);
            Plotly.newPlot('macd-chart', chartData.macd.data, chartData.macd.layout);

            const rsiDiv = document.createElement('div');
            rsiDiv.id = 'rsi-chart';
            indicators.appendChild(rsiDiv);
            Plotly.newPlot('rsi-chart', chartData.rsi.data, chartData.rsi.layout);

            const stochDiv = document.createElement('div');
            stochDiv.id = 'stoch-chart';
            indicators.appendChild(stochDiv);
            Plotly.newPlot('stoch-chart', chartData.stoch.data, chartData.stoch.layout);

            const charts = [
                document.getElementById('chart'),
                document.getElementById('volume-chart'),
                document.getElementById('macd-chart'),
                document.getElementById('rsi-chart'),
                document.getElementById('stoch-chart')
            ];

            charts.forEach(function (chart) {
                chart.on('plotly_relayout', function (eventData) {
                    const xaxis = eventData['xaxis.range[0]'] ?
                        {
                            'xaxis.range[0]': eventData['xaxis.range[0]'],
                            'xaxis.range[1]': eventData['xaxis.range[1]']
                        } : null;

                    if (xaxis) {
                        charts.forEach(function (otherChart) {
                            if (otherChart !== chart) {
                                Plotly.relayout(otherChart, xaxis);
                            }
                        });
                    }
                });
            });
        } else {
            console.error('Plotly.js not loaded.');
        }
    } catch (error) {
        console.error('Error initializing charts:', error);
    }
}

function setupStrategyModal() {
    const strategyModal = document.getElementById('strategyModal');
    const strategyBtn = document.getElementById('strategyBtn');
    const closeStrategyBtn = document.getElementById('closeStrategyModal');
    const saveStrategyBtn = document.getElementById('saveStrategyBtn');
    const resetStrategyBtn = document.getElementById('resetStrategyBtn');

    if (strategyBtn) {
        strategyBtn.addEventListener('click', function () {
            loadCurrentStrategy();
            strategyModal.style.display = 'block';
        });
    }

    setupModalClose(strategyModal, closeStrategyBtn);

    if (saveStrategyBtn) {
        saveStrategyBtn.addEventListener('click', function () {
            saveStrategy();
        });
    }

    if (resetStrategyBtn) {
        resetStrategyBtn.addEventListener('click', function () {
            resetToDefaultStrategy();
        });
    }
}

window.addEventListener('click', function (e) {
    const gemModal = document.getElementById('gemModal');
    const strategyModal = document.getElementById('strategyModal');

    if (e.target == gemModal) {
        gemModal.style.display = 'none';
    }

    if (e.target == strategyModal) {
        strategyModal.style.display = 'none';
    }
});

function loadCurrentStrategy() {
    document.getElementById('strategyForm').style.display = 'none';
    document.getElementById('strategySaveSuccess').style.display = 'none';
    document.getElementById('strategyError').style.display = 'none';

    fetch('/get_strategy')
        .then(response => response.json())
        .then(data => {
            document.getElementById('strategyForm').style.display = 'block';

            if (data.success && data.strategy_params) {
                const params = data.strategy_params;

                document.getElementById('sma_cross').checked = params.sma_cross;
                document.getElementById('macd_signal').checked = params.macd_signal;
                document.getElementById('stoch_signal').checked = params.stoch_signal;
                document.getElementById('bb_strategy').checked = params.bb_strategy;

                document.getElementById('rsi_oversold').value = params.rsi_oversold;
                document.getElementById('rsi_overbought').value = params.rsi_overbought;
                document.getElementById('stoch_oversold').value = params.stoch_oversold;
                document.getElementById('stoch_overbought').value = params.stoch_overbought;
                document.getElementById('min_signals_for_call').value = params.min_signals_for_call;
                document.getElementById('min_signals_for_put').value = params.min_signals_for_put;
            } else {
                resetToDefaultStrategy();
                if (data.error) {
                    console.error('Error loading strategy:', data.error);
                }
            }
        })
        .catch(error => {
            document.getElementById('strategyForm').style.display = 'block';
            console.error('Error fetching strategy:', error);
            resetToDefaultStrategy();
        });
}

function saveStrategy() {
    const strategyParams = {
        sma_cross: document.getElementById('sma_cross').checked,
        macd_signal: document.getElementById('macd_signal').checked,
        stoch_signal: document.getElementById('stoch_signal').checked,
        bb_strategy: document.getElementById('bb_strategy').checked,
        rsi_oversold: parseInt(document.getElementById('rsi_oversold').value),
        rsi_overbought: parseInt(document.getElementById('rsi_overbought').value),
        stoch_oversold: parseInt(document.getElementById('stoch_oversold').value),
        stoch_overbought: parseInt(document.getElementById('stoch_overbought').value),
        min_signals_for_call: parseInt(document.getElementById('min_signals_for_call').value),
        min_signals_for_put: parseInt(document.getElementById('min_signals_for_put').value)
    };

    document.getElementById('strategyForm').style.display = 'none';
    document.getElementById('strategySaveSuccess').style.display = 'none';
    document.getElementById('strategyError').style.display = 'none';

    fetch('/update_strategy', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(strategyParams)
    })
        .then(response => response.json())
        .then(data => {
            document.getElementById('strategyForm').style.display = 'block';

            if (data.success) {
                document.getElementById('strategySaveSuccess').style.display = 'block';

                updLvSig();
                updateCurrentBar();
                setTimeout(() => {
                    document.getElementById('strategySaveSuccess').style.display = 'none';
                }, 3000);
            } else {
                document.getElementById('strategyError').style.display = 'block';
                document.getElementById('strategyErrorTxt').textContent = data.error || 'An error occurred';
            }
        })
        .catch(error => {
            document.getElementById('strategyForm').style.display = 'block';
            document.getElementById('strategyError').style.display = 'block';
            document.getElementById('strategyErrorTxt').textContent = `Error: ${error.message}`;
        });
}

function resetToDefaultStrategy() {
    document.getElementById('sma_cross').checked = true;
    document.getElementById('macd_signal').checked = true;
    document.getElementById('stoch_signal').checked = true;
    document.getElementById('bb_strategy').checked = false;
    document.getElementById('rsi_oversold').value = 30;
    document.getElementById('rsi_overbought').value = 70;
    document.getElementById('stoch_oversold').value = 20;
    document.getElementById('stoch_overbought').value = 80;
    document.getElementById('min_signals_for_call').value = 2;
    document.getElementById('min_signals_for_put').value = 2;
}