from flask import Flask, request, render_template, redirect, session, url_for
import os
import pandas as pd
import qrcode
import subprocess
import requests
import time

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Set a random secret key
app.config['UPLOAD_FOLDER'] = 'attendance_files'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Start ngrok
def start_ngrok():
    ngrok_path = r"C:\ngrok-v3\ngrok.exe"  # Change this to your ngrok path
    subprocess.Popen([ngrok_path, "http", "5000"])
    time.sleep(2)  # Wait for ngrok to start

def get_ngrok_url():
    try:
        response = requests.get("http://127.0.0.1:4040/api/tunnels")
        if response.ok:
            tunnels = response.json()['tunnels']
            if tunnels:
                ngrok_url = tunnels[0]['public_url']
                return ngrok_url
    except Exception as e:
        print(f"Error retrieving ngrok URL: {str(e)}")
    return None

# Store attendance
def record_attendance(roll_no, subject, section):
    file_name = f"{subject}_sec{section}.xlsx"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)

    now = pd.Timestamp.now()
    data = {'Roll No': [roll_no], 'Date': [now.date().strftime('%Y-%m-%d')], 'Time': [now.time().strftime('%H:%M:%S')]}

    if os.path.exists(file_path):
        df = pd.read_excel(file_path)
        df = pd.concat([df, pd.DataFrame(data)], ignore_index=True)
        df.to_excel(file_path, index=False)
    else:
        df = pd.DataFrame(data)
        df.to_excel(file_path, index=False)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        subject = request.form.get('subject')
        username = request.form.get('username')
        password = request.form.get('password')

        # Validate credentials
        valid_username = f"{subject.lower()}_today"  # e.g., ai_today
        valid_password = "java123"

        if username == valid_username and password == valid_password:
            session['subject'] = subject  # Store subject in session
            return redirect(url_for('admin', subject=subject))
        else:
            return "Invalid credentials", 401  # Handle invalid login

    return render_template('admin_login.html')

@app.route('/admin')
def admin():
    subject = session.get('subject')
    if not subject:
        return redirect(url_for('admin_login'))  # Redirect if not logged in

    return render_template('admin.html', subject=subject)

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    subject = request.form.get('subject')
    ngrok_url = get_ngrok_url()  # Get the ngrok URL
    qr_url = f"{ngrok_url}/attendance?subject={subject}"
    qr = qrcode.make(qr_url)
    
    # Save QR code in the static directory
    qr_path = os.path.join(app.static_folder, "qrcode.png")
    qr.save(qr_path)

    return render_template('qrcode.html', qr_image="qrcode.png", ngrok_url=qr_url)

@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    subject = request.args.get('subject')
    if request.method == 'POST':
        roll_no = request.form.get('roll_no').strip().upper()
        section = 'A' if '228W1A5401' <= roll_no <= '228W1A5466' else 'B'
        record_attendance(roll_no, subject, section)

        # After recording attendance, redirect to result.html
        return render_template('result.html', roll_no=roll_no)  # Pass roll_no to the result page

    return render_template('attendance.html', subject=subject)

@app.route('/show_attendance', methods=['GET', 'POST'])
def show_attendance():
    subject = request.args.get('subject')
    section = request.form.get('section', 'A')
    
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{subject}_sec{section}.xlsx")
    attendance_data = pd.read_excel(file_path).to_records(index=False) if os.path.exists(file_path) else []

    return render_template('show_attendance.html', attendance_data=attendance_data, subject=subject)

if __name__ == '__main__':
    start_ngrok()  # Start ngrok when the app starts
    app.run(host='0.0.0.0', port=5000, debug=True)
