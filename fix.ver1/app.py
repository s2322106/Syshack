from flask import Flask, render_template, send_from_directory, request, jsonify
import json
import os
import random

# Create the Flask app with explicit template folder
app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'),
            static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'))

# Define paths to JSON files
USERS_JSON_PATH = '/Users/ady/Desktop/SysHack/Syshack/fix.ver1/users.json'
LEVEL1_QUIZ_PATH = '/Users/ady/Desktop/SysHack/Syshack/fix.ver1/static/level1_quiz_full_50.json'
LEVEL2_QUIZ_PATH = '/Users/ady/Desktop/SysHack/Syshack/fix.ver1/static/level2_quiz_full_50.json'
RESULTS_JSON_PATH = '/Users/ady/Desktop/SysHack/Syshack/fix.ver1/results.json'

# Helper functions to load/save JSON data
def load_users():
    try:
        with open(USERS_JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading users.json: {e}")
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
        else:
            # For level 3, we'll use level 2 for now
            path = LEVEL2_QUIZ_PATH
            
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
    
    return jsonify({'success': False, 'message': 'ユーザー名またはパスワードが正しくありません'})

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
    # Load quiz data for the specified level
    quiz_data = load_quiz_data(level)
    
    # Get questions (handle both formats: "quiz" key or direct list)
    questions = quiz_data.get('quiz', []) if isinstance(quiz_data, dict) else quiz_data
    
    if not questions:
        return jsonify({'success': False, 'message': 'クイズデータが見つかりません'})
    
    # Shuffle and limit to 5 questions
    if len(questions) > 5:
        random.shuffle(questions)
        questions = questions[:5]
    
    # Convert to the format expected by the frontend
    formatted_questions = []
    for q in questions:
        try:
            # Handle different possible formats
            if 'choices' in q and 'answer' in q:
                # Format where answer is the text of the correct choice
                answer_index = q['choices'].index(q['answer'])
                formatted_question = {
                    'question': q['question'],
                    'options': q['choices'],
                    'answer': answer_index
                }
            elif 'options' in q and 'answer' in q and isinstance(q['answer'], int):
                # Format where answer is already the index
                formatted_question = {
                    'question': q['question'],
                    'options': q['options'],
                    'answer': q['answer']
                }
            else:
                # Skip unsupported formats
                continue
                
            formatted_questions.append(formatted_question)
        except Exception as e:
            print(f"Error formatting question: {e}")
            continue
    
    return jsonify({'success': True, 'questions': formatted_questions})

@app.route('/api/quiz-result', methods=['POST'])
def save_quiz_result():
    data = request.get_json()
    
    username = data.get('username')
    level = data.get('level')
    score = data.get('score', 0)
    total = data.get('total', 5)
    answers = data.get('answers', [])
    
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
    
    # Group by username (get latest score for each user)
    user_scores = {}
    for result in level_results:
        username = result.get('username')
        score = result.get('score', 0)
        total = result.get('total', 5)
        
        # Only update if this is a newer result or score is higher
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

@app.route('/api/quiz-history/<username>', methods=['GET'])
def get_quiz_history(username):
    results = load_results()
    
    # Filter results by username
    user_results = [r for r in results if r.get('username') == username]
    
    return jsonify({'success': True, 'history': user_results})

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    app.run(debug=True, port=5001)