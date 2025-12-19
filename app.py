
from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd, os, threading, time, webbrowser, csv

app = Flask(__name__)
DATA_FILE = os.path.join('data','history.csv')

os.makedirs('data', exist_ok=True)
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['amount','merchant','method','is_fraud','source'])
        writer.writeheader()

def rule_based_predict(df):
    df = df.copy()
    def pred(r):
        try:
            amt = float(r.get('amount',0) or 0)
        except:
            amt = 0
        merchant = str(r.get('merchant','') or '').lower()
        method = str(r.get('method','') or '').lower()
        if amt > 50000 and method == 'credit':
            return 1
        if amt > 20000:
            return 1
        if any(k in merchant for k in ['fake','unknown','scam','fraud','suspicious']):
            return 1
        return 0
    df['is_fraud'] = df.apply(pred, axis=1)
    return df

def append_history(df, source='upload'):
    with open(DATA_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['amount','merchant','method','is_fraud','source'])
        for _, row in df.iterrows():
            writer.writerow({'amount': row.get('amount', ''), 'merchant': row.get('merchant',''), 'method': row.get('method',''), 'is_fraud': int(row.get('is_fraud',0)), 'source': source})

@app.route('/')
def home():
    quote = "Digital world without security is like a pyramid without foundation which can collapse like a house of cards"
    images = {
        'home': 'https://advocatetanwar.com/wp-content/uploads/2024/01/How-to-secure-yourself-from-UPI-frauds.webp',
        'upi': 'https://ccoe.dsci.in/storage/blogs/June2024/y1YjAyDCtzWvuRIldJI3.png',
        'credit': 'https://media.licdn.com/dms/image/v2/D5612AQEIF5Tmb__5Dw/article-cover_image-shrink_600_2000/article-cover_image-shrink_600_2000/0/1722662110297?e=2147483647&v=beta&t=IjFDhqbxuMC-qfCypRZLmO-U62RAEF9IJES3V1wF3Oc'
    }
    hero_quote = "Protect every transaction — because trust deserves a strong foundation."
    return render_template('home.html', quote=quote, hero_quote=hero_quote, images=images)

@app.route('/upi')
def upi():
    # page will fetch stats via /stats
    return render_template('fraud_upi.html', title='UPI Fraud', img='https://ccoe.dsci.in/storage/blogs/June2024/y1YjAyDCtzWvuRIldJI3.png', method='upi')

@app.route('/credit')
def credit():
    return render_template('fraud_credit.html', title='Credit Card Fraud', img='https://media.licdn.com/dms/image/v2/D5612AQEIF5Tmb__5Dw/article-cover_image-shrink_600_2000/article-cover_image-shrink_600_2000/0/1722662110297?e=2147483647&v=beta&t=IjFDhqbxuMC-qfCypRZLmO-U62RAEF9IJES3V1wF3Oc', method='credit')

@app.route('/history')
def history():
    df = pd.read_csv(DATA_FILE) if os.path.exists(DATA_FILE) else pd.DataFrame(columns=['amount','merchant','method','is_fraud','source'])
    summary = {
        'total': len(df),
        'fraud': int(df['is_fraud'].sum()) if not df.empty else 0,
        'by_method': df.groupby('method')['is_fraud'].sum().to_dict() if not df.empty else {}
    }
    recent = df.tail(100).to_dict(orient='records') if not df.empty else []
    return render_template('history.html', summary=summary, recent=recent)

@app.route('/stats')
def stats():
    # return aggregated stats for charts
    df = pd.read_csv(DATA_FILE) if os.path.exists(DATA_FILE) else pd.DataFrame(columns=['amount','merchant','method','is_fraud','source'])
    total = len(df)
    fraud = int(df['is_fraud'].sum()) if not df.empty else 0
    by_method = df.groupby('method')['is_fraud'].sum().to_dict() if not df.empty else {}
    method_counts = df['method'].value_counts().to_dict() if not df.empty else {}
    # credit-specific and upi-specific distributions
    credit_df = df[df['method'].str.lower()=='credit'] if not df.empty else pd.DataFrame()
    upi_df = df[df['method'].str.lower()=='upi'] if not df.empty else pd.DataFrame()
    credit_chart = credit_df['is_fraud'].value_counts().to_dict() if not credit_df.empty else {}
    upi_chart = upi_df['is_fraud'].value_counts().to_dict() if not upi_df.empty else {}
    return jsonify({'total': total, 'fraud': fraud, 'by_method': by_method, 'method_counts': method_counts, 'credit_chart': credit_chart, 'upi_chart': upi_chart})

@app.route('/upload', methods=['POST'])
def upload():
    f = request.files.get('file')
    if not f:
        return jsonify({'error':'no file uploaded'}), 400
    try:
        df = pd.read_csv(f)
    except Exception as e:
        return jsonify({'error':str(e)}), 400
    for c in ['amount','merchant','method']:
        if c not in df.columns:
            return jsonify({'error':f'missing column {c}'}), 400
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
    preds = rule_based_predict(df)
    append_history(preds, source='upload')
    chart = preds['is_fraud'].value_counts().to_dict()
    return jsonify({'chart': chart, 'fraud_count': int(preds['is_fraud'].sum()), 'rows': preds.head(50).to_dict(orient='records')})

@app.route('/predict_manual', methods=['POST'])
def predict_manual():
    data = request.json or {}
    try:
        amount = float(data.get('amount',0))
    except:
        amount = 0
    merchant = data.get('merchant','')
    method = data.get('method','').lower()
    df = pd.DataFrame([{'amount': amount, 'merchant': merchant, 'method': method}])
    preds = rule_based_predict(df)
    append_history(preds, source='manual')
    is_fraud = int(preds.loc[0,'is_fraud'])
    return jsonify({'is_fraud': is_fraud})

@app.route('/download-sample')
def download_sample():
    sample_path = os.path.join('data','sample_transactions.csv')
    if not os.path.exists(sample_path):
        df = pd.DataFrame([{'amount':1200,'merchant':'Alpha','method':'credit'},{'amount':50,'merchant':'Grocery','method':'upi'},{'amount':60000,'merchant':'Electro','method':'credit'}])
        df.to_csv(sample_path, index=False)
    return send_file(sample_path, as_attachment=True, download_name='sample_transactions.csv')

def open_browser(port):
    time.sleep(1.0)
    try:
        webbrowser.open(f'http://127.0.0.1:{port}')
    except:
        pass

if __name__=='__main__':
    PORT = 8081
    # open browser automatically
    try:
        threading.Thread(target=open_browser, args=(PORT,), daemon=True).start()
    except:
        pass
    app.run(debug=True, host='0.0.0.0', port=PORT)
