
from flask import Flask, request, render_template, jsonify, session
import io, base64
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import pandas as pd
import yfinance as yf

app = Flask(__name__)
app.secret_key = 'dev-key'  # for session

# ---- Fuzzy Logic Setup ----
profit_margin = ctrl.Antecedent(np.arange(-200, 201, 1), 'Profit Margin')
debt_ratio    = ctrl.Antecedent(np.arange(0, 101, 1), 'Debt Ratio')
roa           = ctrl.Antecedent(np.arange(-100, 101, 1), 'ROA')
price_var     = ctrl.Consequent(np.arange(-50, 51, 1), 'PRICE VAR [%]')

profit_margin['low'] = fuzz.trimf(profit_margin.universe, [-200, -200, 0])
profit_margin['medium'] = fuzz.trimf(profit_margin.universe, [-200, 0, 200])
profit_margin['high'] = fuzz.trimf(profit_margin.universe, [0, 200, 200])

debt_ratio['low'] = fuzz.trimf(debt_ratio.universe, [0, 0, 50])
debt_ratio['medium'] = fuzz.trimf(debt_ratio.universe, [0, 50, 100])
debt_ratio['high'] = fuzz.trimf(debt_ratio.universe, [50, 100, 100])

roa['low'] = fuzz.trimf(roa.universe, [-100, -100, 0])
roa['medium'] = fuzz.trimf(roa.universe, [-100, 0, 100])
roa['high'] = fuzz.trimf(roa.universe, [0, 100, 100])

price_var['decrease'] = fuzz.trimf(price_var.universe, [-50, -50, 0])
price_var['stable'] = fuzz.trimf(price_var.universe, [-50, 0, 50])
price_var['increase'] = fuzz.trimf(price_var.universe, [0, 50, 50])

rule1 = ctrl.Rule(profit_margin['high'] & debt_ratio['low'] & roa['high'], price_var['increase'])
rule2 = ctrl.Rule(profit_margin['medium'] & debt_ratio['medium'] & roa['medium'], price_var['stable'])
rule3 = ctrl.Rule(profit_margin['low'] | debt_ratio['high'] | roa['low'], price_var['decrease'])

pricing_ctrl = ctrl.ControlSystem([rule1, rule2, rule3])
pricing = ctrl.ControlSystemSimulation(pricing_ctrl)

def plot_memberships(active_label=None):
    fig, axes = plt.subplots(nrows=4, figsize=(8,8))
    for ax, antecedent in zip(axes[:3], [profit_margin, debt_ratio, roa]):
        antecedent.view(ax=ax)
    price_var.view(ax=axes[3])
    fig.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', step='input_ratios')

@app.route('/calculate', methods=['POST'])
def calculate():
    company_name = request.form['company_name'].strip()
    pm = float(request.form['profit_margin'])
    dr = float(request.form['debt_ratio'])
    r  = float(request.form['roa'])

    for name, val in [('Profit Margin', pm), ('Debt Ratio', dr), ('ROA', r)]:
        pass

    pricing.input['Profit Margin'] = pm
    pricing.input['Debt Ratio']    = dr
    pricing.input['ROA']           = r
    pricing.compute()
    result = pricing.output['PRICE VAR [%]']

    session['company_name'] = company_name
    session['price_var'] = result

    graph_data = plot_memberships()
    return render_template('index.html', step='enter_stock_price', company_name=company_name, result=result, graph_data=graph_data)

@app.route('/predict_price', methods=['POST'])
def predict_price():
    company_name = request.form['company_name']
    session['company_name'] = company_name
    # current_price could be used to shift predicted line; store it
    try:
        session['current_price'] = float(request.form.get('current_price', '0') or 0)
    except:
        session['current_price'] = 0.0
    return render_template('index.html', step='realtime_graph', company_name=company_name)


@app.route('/realtime-graph-data')
def realtime_graph_data():
    ticker = request.args.get('ticker') or session.get('company_name') or 'AAPL'
    period = '2y'
    try:
        df = yf.download(ticker, period=period, interval='1d', auto_adjust=True, progress=False)
    except Exception as e:
        df = None

    import pandas as pd
    import numpy as np

    # Fallback if yfinance fails or no rows
    if df is None or getattr(df, 'empty', True):
        # synth data (fallback) - ensures the chart renders offline
        idx = pd.date_range(end=pd.Timestamp.today(), periods=500, freq='B')
        close = pd.Series(1000, index=idx).cumsum() * 0.0 + 1000
        # random walk uptrend
        np.random.seed(0)
        close = 1000 + np.cumsum(np.random.normal(1, 10, size=len(idx)))
        df = pd.DataFrame({'Close': close}, index=idx)

    df = df.dropna()
    df = df.tail(600)
    ma5 = df['Close'].rolling(5).mean()
    ma42 = df['Close'].rolling(42).mean()
    ma252 = df['Close'].rolling(252).mean()

    fuzz_pct = float(session.get('price_var', 0.0))
    predicted = df['Close'] * (1.0 + fuzz_pct/100.0)

    payload = {
        'labels': [d.isoformat() for d in df.index],
        'close': [round(float(v), 2) for v in df['Close'].values.tolist()],
        'ma5': [None if pd.isna(v) else round(float(v),2) for v in ma5.values.tolist()],
        'ma42': [None if pd.isna(v) else round(float(v),2) for v in ma42.values.tolist()],
        'ma252': [None if pd.isna(v) else round(float(v),2) for v in ma252.values.tolist()],
        'predicted': [round(float(v),2) for v in predicted.values.tolist()]
    }
    return jsonify(payload)

@app.route('/fuzzy-graph-data')
def fuzzy_graph_data():
    # simple placeholder, mirrors realtime predicted
    fuzz_pct = float(session.get('price_var', 0.0))
    return jsonify({'labels': ['Var'], 'values': [fuzz_pct]})

if __name__ == '__main__':
    app.run(debug=True)
