from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer
import os

# Initialize the Flask app
app = Flask(__name__)

# Configuration
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'pptx', 'docx', 'xlsx'}
app.config['SECRET_KEY'] = 'your_secret_key'
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# In-memory user and file storage (for simplicity)
users = []
uploaded_files = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Routes
@app.route('/ops/login', methods=['POST'])
def ops_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    for user in users:
        if user['username'] == username and user['password'] == password and user['role'] == 'ops':
            return jsonify({'message': 'Ops User logged in successfully!'}), 200

    return jsonify({'error': 'Invalid credentials or not an Ops User.'}), 403

@app.route('/ops/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided.'}), 400

    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        uploaded_files[filename] = {'uploader': 'ops'}
        return jsonify({'message': 'File uploaded successfully!'}), 200

    return jsonify({'error': 'File type not allowed.'}), 400

@app.route('/client/signup', methods=['POST'])
def client_signup():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    encrypted_url = s.dumps(email, salt='email-confirm')
    users.append({'email': email, 'password': password, 'role': 'client', 'verified': False})

    return jsonify({'encrypted_url': encrypted_url}), 201

@app.route('/client/verify', methods=['GET'])
def client_verify():
    token = request.args.get('token')
    try:
        email = s.loads(token, salt='email-confirm', max_age=3600)
        for user in users:
            if user['email'] == email:
                user['verified'] = True
                return jsonify({'message': 'Email verified successfully!'}), 200
    except Exception as e:
        return jsonify({'error': 'Invalid or expired token.'}), 400

@app.route('/client/login', methods=['POST'])
def client_login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    for user in users:
        if user['email'] == email and user['password'] == password and user['role'] == 'client':
            return jsonify({'message': 'Client User logged in successfully!'}), 200

    return jsonify({'error': 'Invalid credentials or not a Client User.'}), 403

@app.route('/client/files', methods=['GET'])
def list_files():
    return jsonify({'files': list(uploaded_files.keys())}), 200

@app.route('/client/download/<filename>', methods=['GET'])
def download_file(filename):
    if filename not in uploaded_files:
        return jsonify({'error': 'File not found.'}), 404

    token = s.dumps(filename, salt='file-download')
    return jsonify({'download_link': f'/download/{token}'}), 200

@app.route('/download/<token>', methods=['GET'])
def secure_download(token):
    try:
        filename = s.loads(token, salt='file-download', max_age=3600)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
    except Exception as e:
        return jsonify({'error': 'Invalid or expired token.'}), 400

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
