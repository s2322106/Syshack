from flask import Flask, render_template, request, jsonify
import json, os
from datetime import datetime

app = Flask(__name__)
RESULTS_FILE = 'results.json'
USERS_FILE = 'users.json'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return app.send_static_file(filename)

@app.route('/api/submit_result', methods=['POST'])
def submit_result():
    data = request.json
    data['timestamp'] = datetime.now().isoformat()
    if not os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, 'w') as f:
            json.dump([], f)
    with open(RESULTS_FILE, 'r+') as f:
        results = json.load(f)
        results.append(data)
        f.seek(0)
        json.dump(results, f, indent=2)
    return jsonify({'status': 'success'})

@app.route('/api/results')
def get_results():
    if not os.path.exists(RESULTS_FILE):
        return jsonify([])
    with open(RESULTS_FILE, 'r') as f:
        data = json.load(f)
    best_scores = {}
    for entry in data:
        key = (entry['username'], entry['level'])
        if key not in best_scores or entry['score'] > best_scores[key]:
            best_scores[key] = entry['score']
    return jsonify([
        {'username': k[0], 'level': k[1], 'max_score': v}
        for k, v in best_scores.items()
    ])

@app.route('/api/register_user', methods=['POST'])
def register_user():
    data = request.json
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump([], f)
    with open(USERS_FILE, 'r+') as f:
        users = json.load(f)
        if any(u['username'] == data['username'] for u in users):
            return jsonify({'status': 'error', 'message': 'ユーザー名は既に存在します'})
        users.append({'username': data['username'], 'password': data['password']})
        f.seek(0)
        json.dump(users, f, indent=2)
    return jsonify({'status': 'success'})

@app.route('/api/login_user', methods=['POST'])
def login_user():
    data = request.json
    if not os.path.exists(USERS_FILE):
        return jsonify({'status': 'error', 'message': '登録されたユーザーがいません'})
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)
        match = next((u for u in users if u['username'] == data['username'] and u['password'] == data['password']), None)
        if match:
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'message': 'ユーザー名またはパスワードが違います'})

if __name__ == '__main__':
    app.run(debug=True)
