from flask import Flask, render_template, request, send_file, redirect, url_for
import pandas as pd
import os
from optimizer_consolidated import run_optimizer

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def format_currency(value):
    return f"{value:,.2f}"

@app.route('/')
def root():
    # Redirect to the login page when the app loads
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Skip authentication and redirect to the index page
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    # Redirect to the login page on logout
    return redirect(url_for('login'))

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    uploaded_file = request.files['file']
    if uploaded_file.filename != '':
        upload_file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
        uploaded_file.save(upload_file_path)

    user_inputs = {
        'Sales Maximization': int(request.form.get('optimization') == 'Sales Maximization'),
        'Profit Maximization': int(request.form.get('optimization') == 'Profit Maximization'),
        'Profitability Maximization': int(request.form.get('optimization') == 'Profitability Maximization'),
        'Quantity Constraint Min': request.form.get('quantity_min', ''),
        'Quantity Constraint Max': request.form.get('quantity_max', ''),
        'Discount % Constraint Min': request.form.get('discount_min', ''),
        'Discount % Constraint Max': request.form.get('discount_max', ''),
        'Sales Constraint Min': request.form.get('sales_min', ''),
        'Sales Constraint Max': request.form.get('sales_max', ''),
        'Profit Constraint Min': request.form.get('profit_min', ''),
        'Profit Constraint Max': request.form.get('profit_max', ''),
        'Profitability Constraint Min': request.form.get('profitability_min', ''),
        'Profitability Constraint Max': request.form.get('profitability_max', ''),
    }

    input_file_path = os.path.join(UPLOAD_FOLDER, 'user_inputs.csv')
    pd.DataFrame([user_inputs]).to_csv(input_file_path, index=False)

    # Unpack the return values from run_optimizer
    final_long_df, total_gmv, total_gp, avg_gp_per = run_optimizer(upload_file_path, input_file_path)

    # Save the results for download
    results_file_path = os.path.join(UPLOAD_FOLDER, 'results.csv')
    final_long_df.to_csv(results_file_path, index=False)

    return render_template(
        'index.html',
        table=final_long_df.to_html(classes='data', index=False),  # Pass the table HTML directly
        titles=final_long_df.columns.values,
        total_gmv=total_gmv,  # Already formatted in run_optimizer
        total_gp=total_gp,    # Already formatted in run_optimizer
        avg_gp_per=avg_gp_per  # Already formatted in run_optimizer
    )

@app.route('/download', methods=['POST'])
def download():
    results_file_path = os.path.join(UPLOAD_FOLDER, 'results.csv')
    return send_file(results_file_path, as_attachment=True)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))