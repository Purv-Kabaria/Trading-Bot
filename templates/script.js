document.addEventListener('DOMContentLoaded', (e) => {
    setupIdxHndlr();
    if (chkInitialFtch())
        updLvSig();

    setInterval(updLvSig, 60000);
    setupGemModal();
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
    } else {
        document.getElementById('live-o').textContent = 'N/A';
        document.getElementById('live-h').textContent = 'N/A';
        document.getElementById('live-l').textContent = 'N/A';
        document.getElementById('live-c').textContent = 'N/A';
        document.getElementById('live-v').textContent = 'N/A';
        document.getElementById('live-sma-s').textContent = 'N/A';
        document.getElementById('live-sma-l').textContent = 'N/A';
        document.getElementById('live-rsi').textContent = 'N/A';
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
    window.onclick = function (e) {
        if (e.target == gModal)
            gModal.style.display = "none";
    }
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

    const smaSPer = 20;
    const smaLPer = 50;
    const rsiPer = 14;

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
        signal: lvSig,
        sma_short_period: smaSPer,
        sma_long_period: smaLPer,
        rsi_period: rsiPer
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