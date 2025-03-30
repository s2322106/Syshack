
from flask import Flask, render_template, send_from_directory, request, jsonify
import json
import os
import random
import base64
import uuid
from datetime import datetime
from google.cloud import vision
import requests
from flask import request
from google.cloud import translate

app = Flask(__name__, static_folder='static')


os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "vision_key.json"

PHOTO_SAVE_DIR = 'static/photos'
PHOTO_RESULTS_PATH = 'photo_results.json'


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(BASE_DIR, "vision_key.json")


  # 서비스 계정 키 경로
DEEPL_API_KEY = "a6da533c-6070-4fb0-a6f4-7e2f57af830b"
GOOGLE_VISION_PUBLIC_KEY = "a6da533c-6070-4fb0-a6f4-7e2f57af830b:fx"

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

# ※ 以下3つのJSONファイルは、レベルごとにクイズ結果を格納するために用意したもの
LEVEL1_RESULTS_JSON_PATH = os.path.join(BASE_DIR, 'level1_results.json')
LEVEL2_RESULTS_JSON_PATH = os.path.join(BASE_DIR, 'level2_results.json')
LEVEL3_RESULTS_JSON_PATH = os.path.join(BASE_DIR, 'level3_results.json')

LEVEL1_QUIZ_PATH = os.path.join(STATIC_DIR, 'level1_quiz_full_50.json')
LEVEL2_QUIZ_PATH = os.path.join(STATIC_DIR, 'level2_quiz_full_50.json')
LEVEL3_QUIZ_PATH = os.path.join(STATIC_DIR, 'level3_quiz_full_50.json')

os.makedirs(PHOTO_SAVE_DIR, exist_ok=True)

import requests

# DeepL 번역 함수 (에러 핸들링 포함)
def translate_to_japanese_deepl(english_name):
    if not DEEPL_API_KEY or DEEPL_API_KEY.strip() == "":
        print("❌ DeepL APIキーが設定されていません。")
        return english_name + "（翻訳エラー）"

    try:
        url = "https://api-free.deepl.com/v2/translate"
        params = {
            "auth_key": DEEPL_API_KEY,
            "text": english_name,
            "target_lang": "JA"
        }
        response = requests.post(url, data=params)

        if response.status_code != 200:
            print(f"❌ DeepL APIエラー: {response.status_code} - {response.text}")
            return english_name + "（翻訳失敗）"

        result = response.json()
        translated_text = result["translations"][0]["text"]
        return translated_text

    except Exception as e:
        print("❌ DeepL翻訳処理中に例外が発生しました:", e)
        return english_name + "（翻訳エラー）"

# 기존 사전 + DeepL 사용
def translate_to_japanese(english_name):
    dictionary = {
        "Bottle": "ボトル",
        "Chair": "椅子",
        "Table": "テーブル",
        "Book": "本"
    }

    if english_name in dictionary:
        return dictionary[english_name]
    else:
        return translate_to_japanese_deepl(english_name)

# from google.cloud import translate_v2 as translate

@app.route('/index.html')
def index_html():
    return render_template('index.html')


@app.route('/api/google-translate', methods=['POST'])
def google_translate():
    try:
        from google.cloud import translate_v2 as translate
        client = translate.Client()
        
        data = request.get_json()
        text = data.get('text', '')
        
        result = client.translate(text, target_language='ja')
        translated = result['translatedText']
        
        return jsonify({'translated_text': translated})
    
    except Exception as e:
        print("翻訳エラー:", e)
        return jsonify({'translated_text': '翻訳失敗'})


################################
# JSON 파일 읽기/쓰기
################################

def load_users():
    """ユーザーデータ(users.json)をロード"""
    try:
        with open(USERS_JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_users(data):
    """ユーザーデータ(users.json)を保存"""
    try:
        with open(USERS_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

@app.route('/api/register_user', methods=['POST'])
def register_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'status': 'error', 'message': 'ユーザー名とパスワードは必須です'})

    users = load_users()

    # 중복 사용자 확인
    if any(user['username'] == username for user in users):
        return jsonify({'status': 'error', 'message': 'このユーザー名は既に使用されています'})

    # 새로운 사용자 추가
    users.append({'username': username, 'password': password})
    save_users(users)

    return jsonify({'status': 'success'})

# ★ レベルごとに結果を読み書きする新しい関数を用意 ★
def load_results_by_level(level):
    """指定レベルの結果ファイルをロード"""
    if level == 1:
        path = LEVEL1_RESULTS_JSON_PATH
    elif level == 2:
        path = LEVEL2_RESULTS_JSON_PATH
    elif level == 3:
        path = LEVEL3_RESULTS_JSON_PATH
    else:
        return []

    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_results_by_level(level, data):
    """指定レベルの結果ファイルに保存"""
    if level == 1:
        path = LEVEL1_RESULTS_JSON_PATH
    elif level == 2:
        path = LEVEL2_RESULTS_JSON_PATH
    elif level == 3:
        path = LEVEL3_RESULTS_JSON_PATH
    else:
        return False

    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False


def load_quiz_data(level):
    """レベルごとのクイズデータをロード"""
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


################################
# 템플릿 라우트
################################

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


################################
# API: 사용자 로그인
################################

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    try:
        with open('users.json', 'r') as f:
            users = json.load(f)
    except Exception:
        return jsonify({'success': False, 'message': 'ユーザーデータを読み込めませんでした'})

    user = next((u for u in users if u['username'] == username), None)

    if not user:
        return jsonify({'success': False, 'message': 'ユーザーが見つかりません'})

    if user['password'] != password:
        return jsonify({'success': False, 'message': 'パスワードが正しくありません'})

    return jsonify({'success': True})



################################
# API: 사용자 등록
################################

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


from flask import request, jsonify
import json

@app.route('/api/update-profile', methods=['POST'])
def update_profile():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    current_password = data.get('currentPassword')
    new_password = data.get('newPassword', None)

    if not username or not current_password:
        return jsonify({'success': False, 'message': '必要な項目が不足しています'})

    # users.json에서 유저 정보 로드
    with open('users.json', 'r') as f:
        users = json.load(f)

    # 사용자 찾기
    user = next((u for u in users if u['username'] == username), None)

    if not user:
        return jsonify({'success': False, 'message': 'ユーザーが見つかりません'})

    if user['password'] != current_password:
        return jsonify({'success': False, 'message': '現在のパスワードが正しくありません'})

    # 이메일 업데이트
    if email:
        user['email'] = email

    # 비밀번호 변경 요청이 있으면 갱신
    if new_password:
        user['password'] = new_password

    # 저장
    with open('users.json', 'w') as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

    return jsonify({'success': True, 'updatedUsername': username})

################################
# API: 퀴즈 데이터 불러오기
################################

@app.route('/api/quiz/<int:level>', methods=['GET'])
def get_quiz_questions(level):
    if level not in [1, 2, 3]:
        return jsonify({'success': False, 'message': '無効なレベルです'})
        
    quiz_data = load_quiz_data(level)
    
    # Get questions (handle different formats)
    questions = []
    if isinstance(quiz_data, dict):
        if 'quiz' in quiz_data:
            questions = quiz_data['quiz']
        else:
            questions = list(quiz_data.values())[0] if quiz_data else []
    elif isinstance(quiz_data, list):
        questions = quiz_data
    
    if not questions:
        return jsonify({'success': False, 'message': 'クイズデータが見つかりません'})
    
    # For continuous quiz - shuffle all questions but don't limit to 5
    random.shuffle(questions)
    
    # Format the questions for the frontend
    formatted_questions = []
    for q in questions:
        try:
            # Skip if there are missing keys
            if 'question' not in q or ('choices' not in q and 'options' not in q):
                continue
                
            # Handle different answer formats
            if 'choices' in q and 'answer' in q:
                if isinstance(q['answer'], str):
                    # Answer is the text, find the index
                    answer_index = q['choices'].index(q['answer'])
                else:
                    # Answer is already an index
                    answer_index = q['answer']
            elif 'options' in q and 'answer' in q:
                if isinstance(q['answer'], str):
                    answer_index = q['options'].index(q['answer'])
                else:
                    answer_index = q['answer']
            elif 'choices' in q and 'correct_answer' in q:
                answer_index = q['choices'].index(q['correct_answer'])
            elif 'options' in q and 'correct_answer' in q:
                answer_index = q['options'].index(q['correct_answer'])
            else:
                continue
            
            # Use whichever options key is available ('choices' or 'options')
            options = q.get('choices', q.get('options', []))
                
            formatted_questions.append({
                'question': q['question'],
                'options': options,
                'answer': answer_index
            })
        except:
            continue
    
    return jsonify({'success': True, 'questions': formatted_questions})


################################
# API: 퀴즈 결과 저장
################################

@app.route('/camera_history.html')
def camera_history():
    return render_template('camera_history.html')

@app.route('/quiz_history.html')
def quiz_history():
    return render_template('quiz_history.html')

@app.route('/profile.html')
def profile():
    return render_template('profile.html')

from datetime import datetime
import os, json
from flask import request, jsonify

@app.route('/api/quiz-result', methods=['POST'])
def save_quiz_result2():
    data = request.get_json()
    level = data.get('level')
    username = data.get('username')
    score = data.get('score', 0)
    total = data.get('total', 50)
    answers = data.get('answers', [])
    overall_timestamp = datetime.now().isoformat()

    if level not in [1, 2, 3]:
        return jsonify({'success': False, 'message': '無効なレベルです'})

    # ✅ 전체 점수 결과 저장용
    result = {
        'username': username,
        'level': level,
        'score': score,
        'total': total,
        'answers': answers,
        'timestamp': overall_timestamp
    }

    # ✅ 단순화된 답안 기록용 (timestamp 추가)
    simplified_answers = []
    for ans in answers:
        simplified_answers.append({
            'question': ans.get('question'),
            'userAnswer': ans.get('userAnswer'),
            'correctAnswer': ans.get('correctAnswer'),
            'correct': ans.get('correct'),
            'timestamp': overall_timestamp
        })

    simplified_log = {
        'username': username,
        'answers': simplified_answers
    }

    level_result_file = f'level{level}_results.json'
    level_answer_file = f'answerlv{level}.json'

    try:
        # 결과 저장
        if os.path.exists(level_result_file):
            with open(level_result_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
        else:
            results = []
        results.append(result)
        with open(level_result_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        # 단순화된 오답 저장
        if os.path.exists(level_answer_file):
            with open(level_answer_file, 'r', encoding='utf-8') as f:
                answer_logs = json.load(f)
        else:
            answer_logs = []
        answer_logs.append(simplified_log)
        with open(level_answer_file, 'w', encoding='utf-8') as f:
            json.dump(answer_logs, f, indent=2, ensure_ascii=False)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


from flask import request, jsonify
from datetime import datetime

@app.route('/api/quiz-result', methods=['POST'])
def save_quiz_result():
    data = request.get_json()
    level = data.get('level')
    username = data.get('username')
    score = data.get('score', 0)
    total = data.get('total', 50)  # Default to 50
    answers = data.get('answers', [])

    if level not in [1, 2, 3]:
        return jsonify({'success': False, 'message': '無効なレベルです'})

    result = {
        'username': username,
        'level': level,
        'score': score,
        'total': total,
        'answers': answers,  # userAnswer, correctAnswer, correct 포함된 상태로
        'timestamp': datetime.now().isoformat()
    }

    results = load_results_by_level(level)
    results.append(result)

    if save_results_by_level(level, results):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': '結果の保存中にエラーが発生しました'})




################################
# API: 퀴즈 랭킹
################################

@app.route('/api/quiz-ranking/<int:level>', methods=['GET'])
def get_quiz_ranking(level):
    if level not in [1, 2, 3]:
        return jsonify({'success': False, 'message': '無効なレベルです'})
        
    # ★ レベルに応じたファイルをロード
    results = load_results_by_level(level)
    level_results = [r for r in results if r.get('level') == level]

    # Group by username (get highest score for each user)
    scores = {}
    for r in level_results:
        name = r.get('username')
        score = r.get('score', 0)
        total = r.get('total', 50)  # Default to 50 for continuous quiz
        
        if name not in scores or scores[name]['score'] < score:
            scores[name] = {
                'username': name,
                'score': score,
                'total': total,
                'percentage': round((score / total) * 100) if total > 0 else 0
            }

    sorted_scores = sorted(scores.values(), key=lambda x: x['score'], reverse=True)
    return jsonify({'success': True, 'rankings': sorted_scores})


## ランキングページを表示
@app.route('/ranking.html')
def show_ranking():
    return render_template('ranking.html')


# (1) レベル1ボタン用のルート
#     /ranking/1 でアクセス
#     level1_results.json読み込み
#---------------------------------
@app.route('/ranking/1')
def show_level1_ranking():
    import os
    import json

    # JSONファイルパス
    json_path = os.path.join(app.root_path, 'level1_results.json')

    # JSON読込
    with open(json_path, 'r', encoding='utf-8') as f:
        all_data = json.load(f)  # リスト [ {...}, {...} ]

    # 1) ユーザー名をキーに、最高スコアが入ったレコードを保存していく
    user_best = {}
    for record in all_data:
        uname = record["username"]
        current_score = record["score"]

        if uname not in user_best:
            # 初めて出てきたユーザーならそのまま登録
            user_best[uname] = record
        else:
            # 既に登録があるユーザーなら、scoreが大きい方を優先
            if current_score > user_best[uname]['score']:
                user_best[uname] = record

    # 2) 最終的にユーザーごとの最高スコアレコードだけが user_best に残っている
    best_list = list(user_best.values())

    # 3) 必要に応じてソート (ここではscore降順)
    best_list.sort(key=lambda x: x["score"], reverse=True)

    # テンプレートへ渡す
    return render_template("level1.html", results=best_list)

@app.route('/camera_history.html')
def camera_history2():
    try:
        photo_folder = os.path.join(app.static_folder, 'photos')
        photo_files = []

        # static/photos 以下の画像ファイル一覧取得（拡張子 jpg/png/jpeg 限定）
        for filename in os.listdir(photo_folder):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                photo_files.append({
                    'image_url': '/static/photos/' + filename,
                    'filename': filename
                })

        # ファイル名で降順ソート（新しい順）
        photo_files.sort(key=lambda x: x['filename'], reverse=True)

        return render_template('camera_history.html', camera_history=photo_files)

    except Exception as e:
        print("写真読み込みエラー:", e)
        return render_template('camera_history.html', camera_history=[])


@app.route('/camera_history.html')
def camera_history1():
    try:
        with open(PHOTO_RESULTS_PATH, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        # DeepL 번역 적용 및 날짜 정렬
        for item in raw_data:
            item['image_url'] = '/static/photos/' + item['filename']

            # 객체 이름 목록 추출
            object_names = [obj['name'] for obj in item.get('objects', [])]
            item['objects'] = object_names

            # 번역된 이름 리스트 생성
            item['translated_objects'] = [translate_to_japanese(name) for name in object_names]

            # 날짜 파싱 (없으면 현재시간)
            try:
                item['timestamp_obj'] = datetime.fromisoformat(item['timestamp'])
            except:
                item['timestamp_obj'] = datetime.now()

        # 최신순 정렬
        sorted_data = sorted(raw_data, key=lambda x: x['timestamp_obj'], reverse=True)

        return render_template('camera_history.html', camera_history=sorted_data)

    except Exception as e:
        print("履歴ロードエラー:", e)
        return render_template('camera_history.html', camera_history=[])

@app.route('/api/photo-history/<username>', methods=['GET'])
def photo_history_by_user(username):
    try:
        if os.path.exists(PHOTO_RESULTS_PATH):
            with open(PHOTO_RESULTS_PATH, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
        else:
            all_data = []

        # 🔑 로그인한 유저의 것만 필터링
        user_data = [entry for entry in all_data if entry.get('username') == username]

        return jsonify({'success': True, 'photos': user_data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e), 'photos': []})



@app.route('/camera_history.html')
def camera_history3():
    try:
        with open(PHOTO_RESULTS_PATH, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        for item in raw_data:
            item['image_url'] = '/static/photos/' + item['filename']
            object_names = [obj['name'] for obj in item.get('objects', [])] if 'objects' in item else [item['en']]
            item['objects'] = object_names
            item['translated_objects'] = [translate_to_japanese(name) for name in object_names]
            try:
                item['timestamp_obj'] = datetime.fromisoformat(item['timestamp'])
            except:
                item['timestamp_obj'] = datetime.now()

        sorted_data = sorted(raw_data, key=lambda x: x['timestamp_obj'], reverse=True)

        return render_template('camera_history.html', camera_history=sorted_data)

    except Exception as e:
        print("履歴ロードエラー:", e)
        return render_template('camera_history.html', camera_history=[])

# (2) レベル2ボタン用のルート
#     /ranking/2 でアクセス
#     level2_results.json読み込み
#---------------------------------
@app.route('/ranking/2')
def show_level2_ranking():
    import os
    import json

    # JSONファイルパス
    json_path = os.path.join(app.root_path, 'level2_results.json')

    # JSON読込
    with open(json_path, 'r', encoding='utf-8') as f:
        all_data = json.load(f)  # リスト [ {...}, {...} ]

    # 1) ユーザー名をキーに、最高スコアが入ったレコードを保存していく
    user_best = {}
    for record in all_data:
        uname = record["username"]
        current_score = record["score"]

        if uname not in user_best:
            user_best[uname] = record
        else:
            if current_score > user_best[uname]['score']:
                user_best[uname] = record

    best_list = list(user_best.values())
    best_list.sort(key=lambda x: x["score"], reverse=True)

    return render_template("level2.html", results=best_list)


#사진 삭제 api

@app.route('/api/delete-photo', methods=['POST'])
def delete_photo():
    try:
        data = request.get_json()
        filename_to_delete = data.get('filename')

        if not filename_to_delete:
            return jsonify({'success': False, 'message': 'ファイル名が指定されていません'})

        # photo_results.json 로드
        if os.path.exists(PHOTO_RESULTS_PATH):
            with open(PHOTO_RESULTS_PATH, 'r', encoding='utf-8') as f:
                records = json.load(f)
        else:
            records = []

        # 해당 filename을 제외한 나머지만 남김
        new_records = [entry for entry in records if entry.get('filename') != filename_to_delete]

        # 파일 업데이트
        with open(PHOTO_RESULTS_PATH, 'w', encoding='utf-8') as f:
            json.dump(new_records, f, ensure_ascii=False, indent=2)

        # 실제 이미지 파일도 삭제 (선택)
        photo_path = os.path.join('static/photos', filename_to_delete)
        if os.path.exists(photo_path):
            os.remove(photo_path)

        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# 사진 좋아요 
@app.route('/api/photo-like-toggle/<photo_id>', methods=['POST'])
def toggle_like(photo_id):
    username = request.json.get('username')
    if not username:
        return jsonify({'success': False, 'message': 'ユーザー名が必要です'}), 400

    with open(PHOTO_RESULTS_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for item in data:
        if item.get('id') == photo_id:
            liked_users = item.get('liked_users', [])
            if username in liked_users:
                liked_users.remove(username)
                item['likes'] = max(item.get('likes', 1) - 1, 0)
            else:
                liked_users.append(username)
                item['likes'] = item.get('likes', 0) + 1
            item['liked_users'] = liked_users
            break

    with open(PHOTO_RESULTS_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return jsonify({'success': True})


# (3) レベル3ボタン用のルート
#     /ranking/3 でアクセス
#     level3_results.json読み込み
#---------------------------------
@app.route('/ranking/3')
def show_level3_ranking():
    import os
    import json

    # JSONファイルパス
    json_path = os.path.join(app.root_path, 'level3_results.json')

    # JSON読込
    with open(json_path, 'r', encoding='utf-8') as f:
        all_data = json.load(f)  # リスト [ {...}, {...} ]

    user_best = {}
    for record in all_data:
        uname = record["username"]
        current_score = record["score"]

        if uname not in user_best:
            user_best[uname] = record
        else:
            if current_score > user_best[uname]['score']:
                user_best[uname] = record

    best_list = list(user_best.values())
    best_list.sort(key=lambda x: x["score"], reverse=True)

    return render_template("level3.html", results=best_list)

#프로필
@app.route('/api/user-profile', methods=['GET'])
def get_user_profile():
    username = request.args.get('username')
    if not username:
        return jsonify({'success': False, 'message': 'ユーザー名が必要です'})

    # 예시로 users.json 에서 사용자 정보를 읽는다고 가정
    try:
        with open('users.json', 'r', encoding='utf-8') as f:
            users = json.load(f)
        for user in users:
            if user.get('username') == username:
                return jsonify({'success': True, 'user': user})
        return jsonify({'success': False, 'message': 'ユーザーが見つかりません'})
    except FileNotFoundError:
        return jsonify({'success': False, 'message': 'ユーザーファイルが存在しません'})



################################
# API: 퀴즈 히스토리
################################


@app.route('/api/quiz-history/<username>', methods=['GET'])
def get_quiz_history(username):
    level = request.args.get('level')

    # level 파라미터가 없는 경우 → 모든 레벨 합산
    if not level:
        all_results = []
        for lvl in [1, 2, 3]:
            results = load_results_by_level(lvl)
            all_results.extend(results)
        user_results = [r for r in all_results if r.get('username') == username]
        user_results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return jsonify({'success': True, 'history': user_results})

    # level 파라미터가 있을 경우 → 특정 레벨 필터링
    if level not in ['1', '2', '3']:
        return jsonify({'success': False, 'message': '無効なレベルです'})

    file_map = {
        '1': 'level1_results.json',
        '2': 'level2_results.json',
        '3': 'level3_results.json'
    }

    filepath = file_map[level]

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            all_results = json.load(f)
    except FileNotFoundError:
        return jsonify({'success': True, 'history': []})

    user_results = [r for r in all_results if r.get('username') == username]
    return jsonify({'success': True, 'history': user_results})


@app.route('/api/quiz-result', methods=['POST'])
def save_quiz_result3():
    data = request.get_json()
    username = data.get('username')
    level = str(data.get('level'))

    if level not in ['1', '2', '3']:
        return jsonify({'success': False, 'message': '無効なレベルです'})

    filename = f'level{level}_results.json'

    new_entry = {
        'username': username,
        'score': data.get('score'),
        'level': level,
        'timestamp': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
        'answers': data.get('answers', [])
    }

    try:
        with open(filename, 'r') as f:
            all_data = json.load(f)
    except FileNotFoundError:
        all_data = []

    all_data.append(new_entry)

    with open(filename, 'w') as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)

    return jsonify({'success': True})

################################
# API: 사진 인식 및 저장
################################

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

        
        object_names = [obj.name for obj in objects]
        translated_names = [translate_to_japanese(name) for name in object_names]
        username = data.get('username')
        
        result_data = {
            "filename": filename,
            "en": object_names,
            "jp": translated_names,
            "username" :username ,
            "timestamp": datetime.now().isoformat()
        }

        save_photo_result(result_data)

        return jsonify({
            'success': True,
            'en': object_names,
            'jp': translated_names,
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
    if english_name in dictionary:
        return dictionary[english_name]

    # fallback: call Google Translate API
    try:
        from google.cloud import translate_v2 as translate
        client = translate.Client()
        result = client.translate(english_name, target_language='ja')
        return result['translatedText']
    except Exception as e:
        print("翻訳エラー:", e)
        return english_name + "（翻訳）"



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


################################
# API: Google Visionキーを取得
################################

@app.route('/api/get-vision-key', methods=['GET'])
def get_vision_key():
    return jsonify({'visionKey': GOOGLE_VISION_PUBLIC_KEY})


################################
# 静的ファイルを提供
################################

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)


################################
# メイン
################################

if __name__ == '__main__':
    # Create results files if they don't exist
    for level in [1, 2, 3]:
        if level == 1 and not os.path.exists(LEVEL1_RESULTS_JSON_PATH):
            save_results_by_level(1, [])
        elif level == 2 and not os.path.exists(LEVEL2_RESULTS_JSON_PATH):
            save_results_by_level(2, [])
        elif level == 3 and not os.path.exists(LEVEL3_RESULTS_JSON_PATH):
            save_results_by_level(3, [])
    
    # 적절히 포트 번호나 호스트 설정

    app.run(host='0.0.0.0', port=5001, debug=True)

