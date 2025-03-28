
from flask import Flask, render_template, send_from_directory, request, jsonify, redirect
import json
import os
import random
import base64
import uuid
from datetime import datetime
from google.cloud import vision
import requests

PHOTO_SAVE_DIR = 'static/photos'
PHOTO_RESULTS_PATH = 'photo_results.json'


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(BASE_DIR, "vision_key.json")


  # 서비스 계정 키 경로
DEEPL_API_KEY = "a6da533c-6070-4fb0-a6f4-7e2f57af830b:fx"
GOOGLE_VISION_PUBLIC_KEY = "3b47c284013af32f47fc63afa13e68bd97a9159c	"

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

# DeepL 번역 함수 추가
def translate_to_japanese_deepl(english_name):
    try:
        url = "https://api-free.deepl.com/v2/translate"
        params = {
            "auth_key": DEEPL_API_KEY,
            "text": english_name,
            "target_lang": "JA"
        }
        response = requests.post(url, data=params)
        result = response.json()
        translated_text = result["translations"][0]["text"]
        return translated_text
    except Exception as e:
        print("DeepL翻訳エラー:", e)
        return english_name + "（翻訳）"

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

# batch_translate_with_deepl
    
def batch_translate_with_deepl(texts, target_lang="EN"):
    """
    Translate multiple texts at once using DeepL API
    """
    if not texts:
        return []
        
    try:
        url = "https://api-free.deepl.com/v2/translate"
        params = []
        for text in texts:
            params.append(("text", text))
        
        params.append(("auth_key", DEEPL_API_KEY))
        params.append(("target_lang", target_lang))
        
        response = requests.post(url, data=params)
        
        if response.status_code == 200:
            result = response.json()
            if "translations" in result:
                return [t["text"] for t in result["translations"]]
        
        print(f"Batch DeepL translation failed: {response.status_code}")
        return texts
    except Exception as e:
        print(f"Error in batch DeepL translation: {e}")
        return texts


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
    return redirect('/quiz.html')

@app.route('/quiz')
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

    # For testing purposes, allow any login
    return jsonify({'success': True, 'username': username})


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
# API: 퀴즈 데이터 불러오기
################################

@app.route('/api/quiz/<int:level>', methods=['GET'])
def get_quiz_questions(level):
    if level not in [1, 2, 3]:
        return jsonify({'success': False, 'message': '無効なレベルです'})
    
    # Get the language parameter from the request (default to Japanese)
    language = request.args.get('lang', 'ja')
    
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
    
    # If English is requested, translate questions and options
    if language == 'en':
        # Create a list for all the texts to translate
        all_texts = []  
        # Keep track of which questions these texts belong to
        questions_map = []
        
        for idx, q in enumerate(questions):
            if 'question' not in q or ('choices' not in q and 'options' not in q):
                continue
                
            # Add the question to the translation list
            all_texts.append(q['question'])
            
            # Determine which options field to use and add all options
            options_field = 'choices' if 'choices' in q else 'options'
            options = q.get(options_field, [])
            
            for option in options:
                all_texts.append(option)
                
            # Map information about this question
            questions_map.append({
                'question_idx': idx,
                'options_field': options_field,
                'options_count': len(options)
            })
                
        # Now translate all texts in one batch if there are any
        if all_texts:
            try:
                # Translate all texts at once
                translated_texts = batch_translate_with_deepl(all_texts, 'EN')
                
                # Map the translations back to the questions
                text_index = 0
                
                for q_map in questions_map:
                    idx = q_map['question_idx']
                    options_field = q_map['options_field']
                    options_count = q_map['options_count']
                    
                    # Get the translated question
                    questions[idx]['question_translated'] = translated_texts[text_index]
                    text_index += 1
                    
                    # Get the translated options
                    translated_options = []
                    for i in range(options_count):
                        translated_options.append(translated_texts[text_index])
                        text_index += 1
                        
                    questions[idx]['options_translated'] = translated_options
            except Exception as e:
                print(f"Translation error: {e}")
    
    # Now format all questions with translations if needed
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
            options_field = 'choices' if 'choices' in q else 'options'
            options = q.get(options_field, [])
            
            # Use translated content if available and English is requested
            question_text = q.get('question', '')
            final_options = options
            
            if language == 'en':
                if 'question_translated' in q:
                    question_text = q['question_translated']
                if 'options_translated' in q:
                    final_options = q['options_translated']
            
            formatted_questions.append({
                'question': question_text,
                'options': final_options,
                'answer': answer_index
            })
        except Exception as e:
            print(f"Error formatting question: {e}")
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

@app.route('/api/quiz-result', methods=['POST'])
def save_quiz_result():
    data = request.get_json()
    level = data.get('level')
    username = data.get('username')
    score = data.get('score', 0)
    total = data.get('total', 50)  # Default to 50 for continuous quiz
    answers = data.get('answers', [])
    language = data.get('language', 'ja')  # Get language but don't do any translation
    
    if level not in [1, 2, 3]:
        return jsonify({'success': False, 'message': '無効なレベルです'})
        
    result = {
        'username': username,
        'level': level,
        'score': score,
        'total': total,
        'answers': answers,
        'language': language,  # Store language for reference
        'timestamp': datetime.now().isoformat()
    }

    # ★ 레벨ごとにファイルを읽어들여、결과を추가して저장
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


################################
# API: 퀴즈 히스토리
################################

## 不正解履歴を表示
@app.route('/api/quiz-history/<username>', methods=['GET'])
def get_quiz_history(username):
    """指定したレベルをクエリパラメータから取得し、当該ユーザーの不正解履歴のみ返す。"""
    # クエリパラメータから level を取得
    level_str = request.args.get('level')
    if not level_str:
        return jsonify({'success': False, 'message': 'レベルが指定されていません'})
    
    try:
        level = int(level_str)
    except:
        return jsonify({'success': False, 'message': 'レベル指定が不正です'})

    if level not in [1, 2, 3]:
        return jsonify({'success': False, 'message': 'レベルは1,2,3のいずれかにしてください'})

    # 指定されたレベルの結果だけ読み込む
    results = load_results_by_level(level)

    # 指定ユーザーの不正解のみ抽出
    user_incorrect_results = []
    for record in results:
        if record.get('username') == username:
            wrong_answers = []
            for ans in record.get('answers', []):
                if ans.get('correct') == False:
                    wrong_answers.append(ans)
            
            # 不正解がある場合、そのレコードを追加
            if len(wrong_answers) > 0:
                # タイムスタンプ順に並べたい場合は最後にソートしてもOK
                user_incorrect_results.append({
                    "username": record.get('username'),
                    "level": record.get('level'),
                    "timestamp": record.get('timestamp', ''),
                    "answers": wrong_answers
                })

    # タイムスタンプで並べ替え (新しい順)
    user_incorrect_results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

    return jsonify({'success': True, 'history': user_incorrect_results})


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
        
        result_data = {
            "filename": filename,
            "en": object_names,
            "jp": translated_names,
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

