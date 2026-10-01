import os
import re
import json
import uuid
import base64
from threading import Lock
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import gspread

app = Flask(__name__)
app.secret_key = 'super_secret_logtime_key'

# Khóa luồng (Lock) để tránh ghi đè dữ liệu khi submit cùng lúc (Race condition)
submit_lock = Lock()

# Cấu hình Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_path = 'credentials.json'
SPREADSHEET_ID = '1nVQ-q4AIxHgknLQac7i-ca1Mpcp0MCpKVesgSgjLn-k'

last_sheet_error = ""

def load_credentials_dict():
    global last_sheet_error
    # 1. Đọc file credentials.json nếu tồn tại
    if os.path.exists(creds_path):
        try:
            with open(creds_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            last_sheet_error = f"Lỗi đọc credentials.json: {e}"
            print(last_sheet_error)

    # 2. Đọc biến môi trường (hỗ trợ cả GOOGLE_CREDENTIALS, GOOGLE_CREDENTIALS_B64, GOOGLE_SHEETS_CREDENTIALS)
    raw_val = (
        os.environ.get('GOOGLE_CREDENTIALS_B64') or
        os.environ.get('GOOGLE_CREDENTIALS') or
        os.environ.get('GOOGLE_SHEETS_CREDENTIALS') or
        ''
    ).strip()

    if not raw_val:
        last_sheet_error = "Chưa cấu hình credentials.json hoặc biến môi trường GOOGLE_CREDENTIALS_B64 / GOOGLE_CREDENTIALS trên server."
        return None

    # Bỏ dấu ngoặc kép bọc ngoài nếu có
    if (raw_val.startswith('"') and raw_val.endswith('"')) or (raw_val.startswith("'") and raw_val.endswith("'")):
        raw_val = raw_val[1:-1].strip()

    # Trường hợp A: Biến là chuỗi JSON trực tiếp
    if raw_val.startswith('{'):
        try:
            return json.loads(raw_val)
        except Exception as e:
            last_sheet_error = f"Lỗi parse JSON credentials: {e}"
            print(last_sheet_error)
            return None

    # Trường hợp B: Biến là chuỗi Base64
    try:
        # Chuẩn hóa URL-safe nếu có
        s = raw_val.replace('-', '+').replace('_', '/')
        # Loại bỏ ký tự thừa ngoài bảng mã Base64
        s = re.sub(r'[^A-Za-z0-9+/=]', '', s)
        s = s.rstrip('=')
        # Thêm padding chuẩn
        s += '=' * ((4 - len(s) % 4) % 4)
        decoded = base64.b64decode(s).decode('utf-8')
        return json.loads(decoded)
    except Exception as e:
        last_sheet_error = f"Lỗi giải mã Base64 GOOGLE_CREDENTIALS: {e}"
        print(last_sheet_error)
        return None

def get_sheet():
    global last_sheet_error
    creds_dict = load_credentials_dict()
    if not creds_dict:
        return None

    # Tự động sửa lỗi ký tự ')' trong private_key nếu có
    if 'private_key' in creds_dict and isinstance(creds_dict['private_key'], str):
        creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
        if 'EKmHf/h)AgMBAAE' in creds_dict['private_key']:
            creds_dict['private_key'] = creds_dict['private_key'].replace('EKmHf/h)AgMBAAE', 'EKmHf/gpAgMBAAE')

    creds = None
    # Thử google.oauth2.service_account trước
    try:
        from google.oauth2.service_account import Credentials
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    except Exception as e1:
        # Fallback oauth2client
        try:
            from oauth2client.service_account import ServiceAccountCredentials
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        except Exception as e2:
            last_sheet_error = f"Lỗi tạo Credentials: {e1} | {e2}"
            print(last_sheet_error)
            return None

    try:
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID)
        last_sheet_error = ""
        return sheet
    except Exception as e:
        last_sheet_error = f"Lỗi kết nối Google Sheets: {e}"
        print(last_sheet_error)
        return None

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        platform_name = request.form.get('platform_name').strip() if request.form.get('platform_name') else ''
        stt = request.form.get('stt').strip() if request.form.get('stt') else ''
        
        if platform_name and stt:
            uid = ''
            hash_val = ''
            col_f = ''
            col_g = ''
            is_valid = False
            sheet_instance = get_sheet()
            if sheet_instance:
                try:
                    hr_sheet = sheet_instance.worksheet("HR Info")
                    rows = hr_sheet.get_all_values()
                    for row in rows[1:]:
                        if len(row) >= 5:
                            if row[4].strip() == platform_name and row[1].strip() == stt:
                                hash_val = row[0].strip() # Lấy cột A (#)
                                uid = row[3].strip()
                                col_f = row[5].strip() if len(row) > 5 else ''
                                col_g = row[6].strip() if len(row) > 6 else ''
                                is_valid = True
                                break
                except Exception as e:
                    print("Lỗi đọc HR Info:", e)
                    return render_template('login.html', error='Lỗi đọc Google Sheets (kiểm tra lại quyền truy cập).')
            else:
                return render_template('login.html', error=last_sheet_error or 'Lỗi kết nối Google Sheets. Vui lòng kiểm tra lại biến môi trường.')
            if is_valid:
                session['platform_name'] = platform_name
                session['stt'] = stt
                session['uid'] = uid
                session['hash_val'] = hash_val
                session['col_f'] = col_f
                session['col_g'] = col_g
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error='Sai Platform Name hoặc Mật khẩu (STT)!')
        else:
            return render_template('login.html', error='Vui lòng nhập Platform Name và STT')
            
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'platform_name' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', 
                           platform_name=session['platform_name'], 
                           stt=session['stt'], 
                           uid=session.get('uid', ''),
                           hash_val=session.get('hash_val', ''),
                           col_f=session.get('col_f', ''),
                           col_g=session.get('col_g', ''))

@app.route('/history')
def history():
    if 'platform_name' not in session:
        return redirect(url_for('login'))
        
    uid = session.get('uid', '').strip()
    user_history = []
    total_minutes = 0
    total_viewer = 0
    
    sheet_instance = get_sheet()
    if sheet_instance:
        try:
            log_sheet = sheet_instance.worksheet("Logtime")
            rows = log_sheet.get_all_values()
            for row in reversed(rows[1:]): # Lấy mới nhất lên đầu
                if len(row) > 2 and row[2].strip() == uid:
                    mins = row[6] if len(row) > 6 else '0'
                    viewer = row[7] if len(row) > 7 else '0'
                    try:
                        total_minutes += int(mins)
                    except ValueError:
                        pass
                    try:
                        total_viewer += int(viewer)
                    except ValueError:
                        pass

                    user_history.append({
                        'date': row[4] if len(row) > 4 else '',
                        'time': row[5] if len(row) > 5 else '',
                        'minutes': mins,
                        'viewer': viewer,
                        'session_id': row[9] if len(row) > 9 else ''
                    })
        except Exception as e:
            print("Lỗi đọc Logtime:", e)
            
    total_time_h = total_minutes // 60
    total_time_m = total_minutes % 60
    total_time_str = f"{total_time_h:02d}:{total_time_m:02d}:00"
            
    return render_template('history.html', 
                           platform_name=session['platform_name'], 
                           stt=session['stt'], 
                           uid=session.get('uid', ''),
                           hash_val=session.get('hash_val', ''),
                           col_f=session.get('col_f', ''),
                           col_g=session.get('col_g', ''),
                           history=user_history,
                           total_minutes=total_minutes,
                           total_viewer=total_viewer,
                           total_time=total_time_str)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/submit_log', methods=['POST'])
def submit_log():
    if 'platform_name' not in session:
        return jsonify({'success': False, 'message': 'Chưa đăng nhập'})
    
    data = request.json
    sheet_instance = get_sheet()
    
    if not sheet_instance:
        return jsonify({'success': False, 'message': 'Chưa cấu hình credentials.json. Data chưa được lưu vào Google Sheet nhưng đã copy báo cáo.'})
    
    try:
        log_sheet = sheet_instance.worksheet("Logtime")
        
        # Tạo mã session duy nhất (vd: SS-1234abcd)
        session_id = f"SS-{str(uuid.uuid4())[:8]}"
        
        # Không đụng vào cột A, chỉ ghi từ B đến J
        row_data = [
            session['stt'],                # B: STT
            data.get('uid', ''),           # C: UID
            session['platform_name'],      # D: Platform Name
            data.get('date', ''),          # E: Date
            data.get('time', ''),          # F: Time
            data.get('minutes', ''),       # G: Minutes
            data.get('live_viewer', ''),   # H: Live Viewer
            data.get('note', ''),          # I: Note
            session_id                     # J: Session ID
        ]
        
        with submit_lock:
            force = data.get('force', False)
            if not force:
                rows = log_sheet.get_all_values()
                uid = data.get('uid', '').strip()
                date = data.get('date', '').strip()
                already_logged = False
                for row in reversed(rows[1:]):
                    if len(row) > 4 and row[2].strip() == uid and row[4].strip() == date:
                        already_logged = True
                        break
                
                if already_logged:
                    return jsonify({'success': False, 'already_logged': True, 'message': 'Bạn đã logtime ngày này rồi. Bạn có muốn logtime thêm không?'})

            col_stt = log_sheet.col_values(2)
            next_row = len(col_stt) + 1
            
            # Dò tìm dòng trống đầu tiên THỰC SỰ (bỏ qua các ô bị dính format/space)
            for i, val in enumerate(col_stt):
                if not str(val).strip(): # Bắt gặp ô trống
                    next_row = i + 1
                    break
                    
            # Đảm bảo sheet có đủ dòng để ghi
            if next_row > log_sheet.row_count:
                log_sheet.add_rows(1)
            
            # Cập nhật từ cột B đến J
            log_sheet.update(range_name=f'B{next_row}:J{next_row}', values=[row_data])
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Lỗi khi lưu: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
