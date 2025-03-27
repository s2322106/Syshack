from flask import Flask, render_template, send_from_directory, request, jsonify
import json
import os

# Create the Flask app with explicit template folder
app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'),
            static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'))

# Get the current directory path
current_dir = os.path.dirname(os.path.abspath(__file__))

# Define paths to JSON files - using absolute paths to avoid errors
USERS_JSON_PATH = os.path.join(current_dir, 'users.json')
LEVEL1_QUIZ_PATH = os.path.join(current_dir, 'static', 'level1_quiz_full_50.json')
LEVEL2_QUIZ_PATH = os.path.join(current_dir, 'static', 'level2_quiz_full_50.json')
LEVEL3_QUIZ_PATH = os.path.join(current_dir, 'static', 'level3_quiz_full_50.json')
RESULTS_JSON_PATH = os.path.join(current_dir, 'results.json')

# Helper functions to load JSON data
def load_users():
    try:
        with open(USERS_JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading users.json: {e}")
        # Create empty users file if it doesn't exist
        save_users([])
        return []

def save_users(users_data):
    try:
        with open(USERS_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving users.json: {e}")
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
            print(f"Invalid level: {level}, defaulting to level 1")
            path = LEVEL1_QUIZ_PATH
            
        print(f"Loading quiz data from: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading quiz data for level {level}: {e}")
        return {"quiz": []}

def load_results():
    try:
        with open(RESULTS_JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading results.json: {e}")
        # Create empty results file if it doesn't exist
        save_results([])
        return []

def save_results(results_data):
    try:
        with open(RESULTS_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving results.json: {e}")
        return False

# Routes for serving templates
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

# API endpoints
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
    print(f"No matching user found, but allowing login for: {username}")
    return jsonify({'success': True, 'username': username})

@app.route('/api/register', methods=['POST'])
def register_api():
    data = request.get_json()
    users = load_users()
    
    username = data.get('username')
    password = data.get('password')
    
    # Check if username already exists
    if any(user.get('username') == username for user in users):
        return jsonify({'success': False, 'message': 'このユーザー名は既に使用されています'})
    
    # Add new user
    users.append({
        'username': username,
        'password': password
    })
    
    if save_users(users):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': 'ユーザー登録中にエラーが発生しました'})

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
    
    # Format the questions for the frontend
    formatted_questions = []
    for idx, q in enumerate(questions):
        try:
            # Skip if there are missing keys
            if not all(key in q for key in ['question', 'choices']):
                print(f"Question {idx} missing required keys. Available keys: {list(q.keys())}")
                continue
                
            # Handle different answer formats
            if 'answer' in q:
                if isinstance(q['answer'], str):
                    # Answer is the text, find the index
                    answer_index = q['choices'].index(q['answer'])
                else:
                    # Answer is already an index
                    answer_index = q['answer']
            elif 'correct_answer' in q:
                answer_index = q['choices'].index(q['correct_answer'])
            else:
                print(f"Question {idx} has no valid answer field")
                continue
                
            formatted_questions.append({
                'question': q['question'],
                'options': q['choices'],
                'answer': answer_index
            })
        except Exception as e:
            print(f"Error formatting question {idx}: {e}")
            continue
    
    print(f"Successfully formatted {len(formatted_questions)} questions")
    return jsonify({'success': True, 'questions': formatted_questions})

@app.route('/api/quiz-result', methods=['POST'])
def save_quiz_result():
    data = request.get_json()
    
    username = data.get('username')
    level = data.get('level')
    score = data.get('score', 0)
    total = data.get('total', 0)
    answers = data.get('answers', [])
    
    print(f"Saving quiz result for user: {username}, level: {level}, score: {score}/{total}")
    
    # Create result entry
    result = {
        'username': username,
        'level': level,
        'score': score,
        'total': total,
        'answers': answers,
        'timestamp': '__timestamp__'  # In a real app, use datetime
    }
    
    # Load and update results
    results = load_results()
    results.append(result)
    
    if save_results(results):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': '結果の保存中にエラーが発生しました'})

@app.route('/api/quiz-ranking/<int:level>', methods=['GET'])
def get_quiz_ranking(level):
    results = load_results()
    
    # Filter results by level
    level_results = [r for r in results if r.get('level') == level]
    
    # Group by username (get highest score for each user)
    user_scores = {}
    for result in level_results:
        username = result.get('username')
        score = result.get('score', 0)
        total = result.get('total', 0)
        
        # Only update if this score is higher
        if username not in user_scores or user_scores[username]['score'] < score:
            user_scores[username] = {
                'username': username,
                'score': score,
                'total': total,
                'percentage': round((score / total) * 100) if total > 0 else 0
            }
    
    # Convert to list and sort by score
    rankings = list(user_scores.values())
    rankings.sort(key=lambda x: x['score'], reverse=True)
    
    return jsonify({'success': True, 'rankings': rankings})

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    # Print debug information
    print(f"Current working directory: {current_dir}")
    print(f"Users file path: {USERS_JSON_PATH}")
    print(f"Level 1 quiz path: {LEVEL1_QUIZ_PATH}")
    print(f"Level 2 quiz path: {LEVEL2_QUIZ_PATH}")
    print(f"Level 3 quiz path: {LEVEL3_QUIZ_PATH}")
    print(f"Results file path: {RESULTS_JSON_PATH}")
    
    # Check if quiz files exist
    print(f"Level 1 quiz exists: {os.path.exists(LEVEL1_QUIZ_PATH)}")
    print(f"Level 2 quiz exists: {os.path.exists(LEVEL2_QUIZ_PATH)}")
    print(f"Level 3 quiz exists: {os.path.exists(LEVEL3_QUIZ_PATH)}")
    
    # Create results file if it doesn't exist
    if not os.path.exists(RESULTS_JSON_PATH):
        save_results([])
        print("Created empty results.json file")
    
    # Create users file if it doesn't exist
    if not os.path.exists(USERS_JSON_PATH):
        save_users([])
        print("Created empty users.json file")
    
    app.run(debug=True, port=5001)