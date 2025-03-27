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

# ※ 以下3つのJSONファイルは、レベルごとにクイズ結果を格納するために用意したもの
LEVEL1_RESULTS_JSON_PATH = os.path.join(BASE_DIR, 'level1_results.json')
LEVEL2_RESULTS_JSON_PATH = os.path.join(BASE_DIR, 'level2_results.json')
LEVEL3_RESULTS_JSON_PATH = os.path.join(BASE_DIR, 'level3_results.json')

LEVEL1_QUIZ_PATH = os.path.join(STATIC_DIR, 'level1_quiz_full_50.json')
LEVEL2_QUIZ_PATH = os.path.join(STATIC_DIR, 'level2_quiz_full_50.json')
LEVEL3_QUIZ_PATH = os.path.join(STATIC_DIR, 'level3_quiz_full_50.json')

os.makedirs(PHOTO_SAVE_DIR, exist_ok=True)


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
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading results for level {level}: {e}")
        # Create empty file if it doesn't exist
        save_results_by_level(level, [])
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
            print(f"Invalid level: {level}, defaulting to level 1")
            path = LEVEL1_QUIZ_PATH
            
        print(f"Loading quiz data from: {path}")
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
def login_api():
    data = request.get_json()
    users = load_users()
    username = data.get('username')
    password = data.get('password')

    for user in users:
        if user.get('username') == username and user.get('password') == password:
            return jsonify({'success': True, 'username': username})

    return jsonify({'success': False, 'message': 'ユーザー名またはパスワードが正しくありません'})


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


################################
# API: 퀴즈 데이터 불러오기 (IMPROVED)
################################

@app.route('/api/quiz/<int:level>', methods=['GET'])
def get_quiz_questions(level):
    print(f"Received request for quiz level: {level}")
    
    if level not in [1, 2, 3]:
        print(f"Invalid level requested: {level}")
        return jsonify({'success': False, 'message': '無効なレベルです'})
        
    quiz_data = load_quiz_data(level)
    print(f"Loaded quiz data with structure: {type(quiz_data)}")
    
    # Get questions (handle different formats)
    questions = []
    if isinstance(quiz_data, dict):
        if 'quiz' in quiz_data:
            questions = quiz_data['quiz']
        else:
            questions = list(quiz_data.values())[0]  # Try first key
    elif isinstance(quiz_data, list):
        questions = quiz_data
    
    print(f"Extracted {len(questions)} questions")
    
    if not questions:
        return jsonify({'success': False, 'message': 'クイズデータが見つかりません'})
    
    # 5問抽出して返す
    if len(questions) > 5:
        random.shuffle(questions)
        questions = questions[:5]
    
    # Format the questions for the frontend
    formatted_questions = []
    for idx, q in enumerate(questions):
        try:
            # Skip if there are missing keys
            if 'question' not in q:
                print(f"Question {idx} missing required 'question' key. Available keys: {list(q.keys())}")
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
                print(f"Question {idx} has no valid answer field or format is unexpected")
                continue
            
            # Use whichever options key is available ('choices' or 'options')
            options = q.get('choices', q.get('options', []))
                
            formatted_questions.append({
                'question': q['question'],
                'options': options,
                'answer': answer_index
            })
        except Exception as e:
            print(f"Error formatting question {idx}: {e}")
            continue
    
    print(f"Successfully formatted {len(formatted_questions)} questions")
    return jsonify({'success': True, 'questions': formatted_questions})


################################
# API: 퀴즈 결과 저장 (IMPROVED)
################################

@app.route('/api/quiz-result', methods=['POST'])
def save_quiz_result():
    data = request.get_json()
    level = data.get('level')
    
    if level not in [1, 2, 3]:
        return jsonify({'success': False, 'message': '無効なレベルです'})
        
    result = {
        'username': data.get('username'),
        'level': level,
        'score': data.get('score', 0),
        'total': data.get('total', 5),
        'answers': data.get('answers', []),
        'timestamp': datetime.now().isoformat()
    }

    print(f"Saving quiz result for user: {result['username']}, level: {level}, score: {result['score']}/{result['total']}")

    # ★ 레벨ごとにファイルを読み込み、結果を追加して保存
    results = load_results_by_level(level)
    results.append(result)

    if save_results_by_level(level, results):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': '結果の保存中にエラーが発生しました'})


################################
# API: 퀴즈 랭킹 (IMPROVED)
################################

@app.route('/api/quiz-ranking/<int:level>', methods=['GET'])
def get_quiz_ranking(level):
    if level not in [1, 2, 3]:
        return jsonify({'success': False, 'message': '無効なレベルです'})
        
    # ★ レベルに応じたファイルをロード
    results = load_results_by_level(level)
    
    # Filter by level again to be safe
    level_results = [r for r in results if r.get('level') == level]

    # Group by username (get highest score for each user)
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
                'percentage': round((score / total) * 100) if total > 0 else 0
            }

    sorted_scores = sorted(scores.values(), key=lambda x: x['score'], reverse=True)
    return jsonify({'success': True, 'rankings': sorted_scores})


## ランキングページを表示
@app.route('/ranking.html')
def show_ranking():
    return render_template('ranking.html')

# (2) レベル1ボタン用のルート
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

    # 3) 必要に応じてソート(ここではscore降順)
    best_list.sort(key=lambda x: x["score"], reverse=True)

    # テンプレートへ渡す
    return render_template("level1.html", results=best_list)

# (2) レベル2ボタン用のルート
#     /ranking/2 でアクセス
#     level2_results.json読み込み
#---------------------------------


# (2) レベル1ボタン用のルート
#     /ranking/1 でアクセス
#     level1_results.json読み込み
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
            # 初めて出てきたユーザーならそのまま登録
            user_best[uname] = record
        else:
            # 既に登録があるユーザーなら、scoreが大きい方を優先
            if current_score > user_best[uname]['score']:
                user_best[uname] = record
    
    # 2) 最終的にユーザーごとの最高スコアレコードだけが user_best に残っている
    best_list = list(user_best.values())

    # 3) 必要に応じてソート(ここではscore降順)
    best_list.sort(key=lambda x: x["score"], reverse=True)

    # テンプレートへ渡す
    return render_template("level2.html", results=best_list)

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

    # 3) 必要に応じてソート(ここではscore降順)
    best_list.sort(key=lambda x: x["score"], reverse=True)

    # テンプレートへ渡す
    return render_template("level3.html", results=best_list)


################################
# API: 퀴즈 히스토리 (IMPROVED)
################################

@app.route('/api/quiz-history/<username>', methods=['GET'])
def get_quiz_history(username):
    # 全レベルのファイルを合算してユーザー履歴を取得
    all_results = []
    for lvl in [1, 2, 3]:
        results = load_results_by_level(lvl)
        all_results.extend(results)

    user_results = [r for r in all_results if r.get('username') == username]
    
    # Sort by timestamp (newest first)
    user_results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    return jsonify({'success': True, 'history': user_results})


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
    # 簡易辞書（実際には外部APIを使うかもっとデータを増やすなどで対応）
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
    # Check if quiz files exist
    print(f"Level 1 quiz exists: {os.path.exists(LEVEL1_QUIZ_PATH)}")
    print(f"Level 2 quiz exists: {os.path.exists(LEVEL2_QUIZ_PATH)}")
    print(f"Level 3 quiz exists: {os.path.exists(LEVEL3_QUIZ_PATH)}")
    
    # Create results files if they don't exist
    for level in [1, 2, 3]:
        if level == 1 and not os.path.exists(LEVEL1_RESULTS_JSON_PATH):
            save_results_by_level(1, [])
            print("Created empty level1_results.json file")
        elif level == 2 and not os.path.exists(LEVEL2_RESULTS_JSON_PATH):
            save_results_by_level(2, [])
            print("Created empty level2_results.json file")
        elif level == 3 and not os.path.exists(LEVEL3_RESULTS_JSON_PATH):
            save_results_by_level(3, [])
            print("Created empty level3_results.json file")
    
    # 적절히 포트 번호나 호스트 설정
    app.run(host='0.0.0.0', port=5000, debug=True)