from flask import Flask, render_template, send_from_directory, request, jsonify
import json
import os
import random
import base64
import uuid
from datetime import datetime
from google.cloud import vision
import requests

# 환경 변수 하드코딩 (주의: 실제 서비스에서는 보안상 위험함)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "vision_key.json"  # 서비스 계정 키 경로
DEEPL_API_KEY = "YOUR_DEEPL_API_KEY"
GOOGLE_VISION_PUBLIC_KEY = "AIzaSyDh3F0OXIC4a-V7hd9Z6duLA_9UJ7YOV74"

# Flask 앱 생성
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'),
    static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
)

# 상대 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
PHOTO_SAVE_DIR = os.path.join(STATIC_DIR, 'photos')
PHOTO_RESULTS_PATH = os.path.join(BASE_DIR, 'photo_results.json')

USERS_JSON_PATH = os.path.join(BASE_DIR, 'users.json')
RESULTS_JSON_PATH = os.path.join(BASE_DIR, 'results.json')
LEVEL1_QUIZ_PATH = os.path.join(STATIC_DIR, 'level1_quiz_full_50.json')
LEVEL2_QUIZ_PATH = os.path.join(STATIC_DIR, 'level2_quiz_full_50.json')
LEVEL3_QUIZ_PATH = os.path.join(STATIC_DIR, 'level3_quiz_full_50.json')

os.makedirs(PHOTO_SAVE_DIR, exist_ok=True)




# JSON 파일 읽기/쓰기

def load_users():
    try:
        with open(USERS_JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_users(data):
    try:
        with open(USERS_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def load_results():
    try:
        with open(RESULTS_JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_results(data):
    try:
        with open(RESULTS_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def load_quiz_data(level):
    try:
        if level == 1:
            path = LEVEL1_QUIZ_PATH
        elif level == 2:
            path = LEVEL2_QUIZ_PATH
        elif level == 3:
            path = LEVEL3_QUIZ_PATH
        else:
            return {"quiz": []}

        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading quiz data for level {level}: {e}")
        return {"quiz": []}

# 템플릿 라우트
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/main.html')
def main():
    return render_template('main.html')

@app.route('/quiz.html')
def quiz():
    return render_template('quiz.html')

@app.route('/camera.html')
def camera():
    return render_template('camera.html')

@app.route('/menu.html')
def menu():
    try:
        return render_template('Menu.html')
    except:
        return render_template('menu.html')

# API: 사용자 로그인
@app.route('/api/login', methods=['POST'])
def login_api():
    data = request.get_json()
    users = load_users()
    username = data.get('username')
    password = data.get('password')

    for user in users:
        if user.get('username') == username and user.get('password') == password:
            return jsonify({'success': True, 'username': username})

    return jsonify({'success': False, 'message': 'ユーザー名またはパスワードが正しくありません'})

# API: 사용자 등록
@app.route('/api/register', methods=['POST'])
def register_api():
    data = request.get_json()
    users = load_users()
    username = data.get('username')
    password = data.get('password')

    if any(user.get('username') == username for user in users):
        return jsonify({'success': False, 'message': 'このユーザー名は既に使用されています'})

    users.append({'username': username, 'password': password})

    if save_users(users):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'ユーザー登録中にエラーが発生しました'})

# API: 퀴즈 데이터 불러오기
@app.route('/api/quiz/<int:level>', methods=['GET'])
def get_quiz_questions(level):
    quiz_data = load_quiz_data(level)
    questions = quiz_data.get('quiz', []) if isinstance(quiz_data, dict) else quiz_data

    if not questions:
        return jsonify({'success': False, 'message': 'クイズデータが見つかりません'})

    if len(questions) > 5:
        random.shuffle(questions)
        questions = questions[:5]

    formatted = []
    for q in questions:
        try:
            if 'choices' in q and 'answer' in q:
                idx = q['choices'].index(q['answer'])
                formatted.append({'question': q['question'], 'options': q['choices'], 'answer': idx})
            elif 'options' in q and isinstance(q['answer'], int):
                formatted.append({'question': q['question'], 'options': q['options'], 'answer': q['answer']})
        except:
            continue

    return jsonify({'success': True, 'questions': formatted})

# API: 퀴즈 결과 저장
@app.route('/api/quiz-result', methods=['POST'])
def save_quiz_result():
    data = request.get_json()
    result = {
        'username': data.get('username'),
        'level': data.get('level'),
        'score': data.get('score', 0),
        'total': data.get('total', 5),
        'answers': data.get('answers', []),
        'timestamp': datetime.now().isoformat()
    }

    results = load_results()
    results.append(result)

    if save_results(results):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': '結果の保存中にエラーが発生しました'})

# API: 퀴즈 랭킹
@app.route('/api/quiz-ranking/<int:level>', methods=['GET'])
def get_quiz_ranking(level):
    results = load_results()
    level_results = [r for r in results if r.get('level') == level]

    scores = {}
    for r in level_results:
        name = r.get('username')
        score = r.get('score', 0)
        total = r.get('total', 5)
        if name not in scores or scores[name]['score'] < score:
            scores[name] = {
                'username': name,
                'score': score,
                'total': total,
                'percentage': round((score / total) * 100) if total else 0
            }

    sorted_scores = sorted(scores.values(), key=lambda x: x['score'], reverse=True)
    return jsonify({'success': True, 'rankings': sorted_scores})

# API: 퀴즈 히스토리
@app.route('/api/quiz-history/<username>', methods=['GET'])
def get_quiz_history(username):
    results = load_results()
    user_results = [r for r in results if r.get('username') == username]
    return jsonify({'success': True, 'history': user_results})

# API: 사진 인식 및 저장
@app.route('/api/photo-analyze', methods=['POST'])
def photo_analyze():
    try:
        data = request.get_json()
        image_data = data.get('image')

        if not image_data:
            return jsonify({'success': False, 'message': '画像がありません'}), 400

        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]

        image_bytes = base64.b64decode(image_data)
        filename = f"{uuid.uuid4().hex}.png"
        filepath = os.path.join(PHOTO_SAVE_DIR, filename)

        with open(filepath, 'wb') as f:
            f.write(image_bytes)

        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_bytes)
        response = client.object_localization(image=image)
        objects = response.localized_object_annotations

        if not objects:
            return jsonify({'success': False, 'message': '物体が検出されませんでした'})

        first_obj = objects[0].name
        jp_translation = translate_to_japanese(first_obj)

        result_data = {
            "filename": filename,
            "en": first_obj,
            "jp": jp_translation,
            "timestamp": datetime.now().isoformat()
        }

        save_photo_result(result_data)

        return jsonify({
            'success': True,
            'en': first_obj,
            'jp': jp_translation,
            'objects': [{
                'name': obj.name,
                'boundingPoly': {
                    'normalizedVertices': [
                        {'x': v.x, 'y': v.y} for v in obj.bounding_poly.normalized_vertices
                    ]
                },
                'score': obj.score
            } for obj in objects]
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/photo-history', methods=['GET'])
def photo_history():
    try:
        if os.path.exists(PHOTO_RESULTS_PATH):
            with open(PHOTO_RESULTS_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = []

        return jsonify({'success': True, 'photos': data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e), 'photos': []})

def translate_to_japanese(english_name):
    dictionary = {
        "Bottle": "ボトル",
        "Chair": "椅子",
        "Table": "テーブル",
        "Book": "本"
    }
    return dictionary.get(english_name, english_name + "（翻訳）")

def save_photo_result(entry):
    try:
        if os.path.exists(PHOTO_RESULTS_PATH):
            with open(PHOTO_RESULTS_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = []

        data.append(entry)

        with open(PHOTO_RESULTS_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print("保存エラー:", e)

@app.route('/api/get-vision-key', methods=['GET'])
def get_vision_key():
    return jsonify({'visionKey': "AIzaSyDh3F0OXIC4a-V7hd9Z6duLA_9UJ7YOV74"})

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    app.run(debug=True, port=5001)