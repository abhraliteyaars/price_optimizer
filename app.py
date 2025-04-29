from flask import Flask, render_template, request, send_file, redirect, url_for, session
import pandas as pd
import os
from optimizer_consolidated import run_optimizer
from datetime import datetime
import re

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Required for session
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
    # Load saved inputs from session if they exist
    saved_inputs = session.get('user_inputs', {})
    return render_template('index.html', saved_inputs=saved_inputs, last_uploaded_file=session.get('last_uploaded_file'))

@app.route('/process', methods=['POST'])
def process():
    error_message = None
    uploaded_file = request.files['file']
    # Validate file upload
    if uploaded_file.filename == '':
        error_message = "Please upload a CSV file."
    elif not uploaded_file.filename.lower().endswith('.csv'):
        error_message = "Only CSV files are supported."

    # Clean up % signs and whitespace for quantity and profitability constraints
    def clean_percent(val):
        if val is None:
            return ''
        return str(val).replace('%', '').strip()

    # Save user inputs to session
    user_inputs = {
        'optimization': request.form.get('optimization'),
        'quantity_min': clean_percent(request.form.get('quantity_min', '')),
        'quantity_max': clean_percent(request.form.get('quantity_max', '')),
        'discount_min': request.form.get('discount_min', ''),
        'discount_max': request.form.get('discount_max', ''),
        'sales_min': request.form.get('sales_min', ''),
        'sales_max': request.form.get('sales_max', ''),
        'profit_min': request.form.get('profit_min', ''),
        'profit_max': request.form.get('profit_max', ''),
        'profitability_min': clean_percent(request.form.get('profitability_min', '')),
        'profitability_max': clean_percent(request.form.get('profitability_max', '')),
    }
    session['user_inputs'] = user_inputs

    # Validate numeric fields (allow empty, but if not empty, must be a number)
    numeric_fields = [
        'quantity_min', 'quantity_max', 'discount_min', 'discount_max',
        'sales_min', 'sales_max', 'profit_min', 'profit_max',
        'profitability_min', 'profitability_max'
    ]
    for field in numeric_fields:
        val = user_inputs[field]
        if val and not re.match(r'^-?\d+(\.\d+)?$', val):
            error_message = f"'{field.replace('_', ' ').title()}' must be a number."
            break

    if error_message:
        return render_template(
            'index.html',
            saved_inputs=user_inputs,
            last_uploaded_file=session.get('last_uploaded_file'),
            error_message=error_message
        )

    # Save uploaded file with original filename (no timestamp)
    filename = uploaded_file.filename
    upload_file_path = os.path.join(UPLOAD_FOLDER, filename)
    uploaded_file.save(upload_file_path)
    session['last_uploaded_file'] = filename

    # Prepare inputs for optimizer
    optimizer_inputs = {
        'Sales Maximization': int(user_inputs['optimization'] == 'Sales Maximization'),
        'Profit Maximization': int(user_inputs['optimization'] == 'Profit Maximization'),
        'Profitability Maximization': int(user_inputs['optimization'] == 'Profitability Maximization'),
        'Quantity Constraint Min': user_inputs['quantity_min'],
        'Quantity Constraint Max': user_inputs['quantity_max'],
        'Discount % Constraint Min': user_inputs['discount_min'],
        'Discount % Constraint Max': user_inputs['discount_max'],
        'Sales Constraint Min': user_inputs['sales_min'],
        'Sales Constraint Max': user_inputs['sales_max'],
        'Profit Constraint Min': user_inputs['profit_min'],
        'Profit Constraint Max': user_inputs['profit_max'],
        'Profitability Constraint Min': user_inputs['profitability_min'],
        'Profitability Constraint Max': user_inputs['profitability_max'],
    }
    input_file_path = os.path.join(UPLOAD_FOLDER, 'user_inputs.csv')
    pd.DataFrame([optimizer_inputs]).to_csv(input_file_path, index=False)

    # Run optimizer
    try:
        final_long_df, total_gmv, total_gp, avg_gp_per, total_base_gmv, total_base_gp, avg_base_gp_per = run_optimizer(upload_file_path, input_file_path)
    except Exception as e:
        error_message = f"There was an error processing your file or inputs: {str(e)}"
        return render_template(
            'index.html',
            saved_inputs=user_inputs,
            last_uploaded_file=session.get('last_uploaded_file'),
            error_message=error_message
        )

    # Save results with a fixed filename (overwrite each time)
    results_file_path = os.path.join(UPLOAD_FOLDER, 'results.csv')
    final_long_df.to_csv(results_file_path, index=False)
    session['last_results_file'] = 'results.csv'

    return render_template(
        'index.html',
        table=final_long_df.to_html(classes='data', index=False),
        titles=final_long_df.columns.values,
        total_gmv=total_gmv,
        total_gp=total_gp,
        avg_gp_per=avg_gp_per,
        total_base_gmv=total_base_gmv,
        total_base_gp=total_base_gp,
        avg_base_gp_per=avg_base_gp_per,
        saved_inputs=user_inputs,
        last_uploaded_file=session.get('last_uploaded_file'),
        error_message=None
    )

@app.route('/download', methods=['POST'])
def download():
    results_file = session.get('last_results_file', 'results.csv')
    results_file_path = os.path.join(UPLOAD_FOLDER, results_file)
    return send_file(results_file_path, as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
