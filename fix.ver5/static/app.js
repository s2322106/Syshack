import config from './api-config.js';

new Vue({
  el: '#app',
  delimiters: ['[[', ']]'],
  data: {
    loginUsername: '',
    loginPassword: '',
    registerUsername: '',
    registerPassword: '',
    error: '',
    page: 'login',
    currentQuestionSet: [],
    currentQuestionIndex: 0,
    selectedOption: null,
    quizCompleted: false,
    correct: false,
    correctCount: 0,
    videoStarted: false,
    boxes: [],
    translatedLabel: ''
  },
  computed: {
    currentQuestion() {
      return this.currentQuestionSet[this.currentQuestionIndex];
    }
  },
  methods: {
    toggleForm() {
      this.error = '';
      this.page = this.page === 'login' ? 'register' : 'login';
    },
    async login() {
      const res = await fetch('/api/login_user', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: this.loginUsername,
          password: this.loginPassword
        })
      });
      const data = await res.json();
      if (data.status === 'success') {
        this.page = 'select';
        this.error = '';
      } else {
        this.error = data.message;
      }
    },
    async register() {
      if (this.registerUsername && this.registerPassword) {
        const res = await fetch('/api/register_user', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: this.registerUsername,
            password: this.registerPassword
          })
        });
        const data = await res.json();
        if (data.status === 'success') {
          this.error = '';
          this.page = 'login';
        } else {
          this.error = data.message;
        }
      } else {
        this.error = '全てのフィールドを入力してください';
      }
    },
    goToPage(page) {
      this.page = page;
      if (page === 'camera' && !this.videoStarted) {
        this.startCamera();
      }
      if (page === 'quiz') {
        this.resetQuiz();
      }
    },
    async selectLevel(level) {
      const fileName = '/static/level' + (level === 'easy' ? '1' : level === 'medium' ? '2' : '3') + '_quiz_full_50.json';
      const res = await fetch(fileName);
      const json = await res.json();
      const data = json.quiz; // JSON 파일이 { quiz: [...] } 구조이므로 quiz 배열에 접근
      const shuffled = data.sort(() => Math.random() - 0.5);
      this.currentQuestionSet = shuffled.map(q => ({
        question: q.question,
        options: q.choices,
        answer: q.choices.indexOf(q.answer),
        level: q.level
      }));
      this.page = 'quiz';
      this.resetQuiz();
    },
    selectOption(index) {
      if (this.selectedOption === null) {
        this.selectedOption = index;
        this.correct = index === this.currentQuestion.answer;
        this.quizCompleted = true;

        if (this.correct) {
          this.correctCount++;
          this.page = 'result';
        } else {
          this.page = 'quiz-finished';
        }
      }
    },
    nextQuestion() {
      this.currentQuestionIndex++;
      if (this.currentQuestionIndex >= this.currentQuestionSet.length) {
        this.page = 'quiz-finished';
      } else {
        this.quizCompleted = false;
        this.selectedOption = null;
        this.page = 'quiz';
      }
    },
    resetQuiz() {
      this.currentQuestionIndex = 0;
      this.selectedOption = null;
      this.quizCompleted = false;
      this.correct = false;
      this.correctCount = 0;
    },
    async submitQuizResult() {
      const payload = {
        username: this.loginUsername,
        level: this.currentQuestionSet[0]?.level || 0,
        score: this.correctCount
      };
      await fetch('/api/submit_result', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      alert("結果が保存されました！");
      this.page = 'select';
    },
    startCamera() {
      const video = this.$refs.video;
      const canvas = this.$refs.canvas;
      const ctx = canvas.getContext('2d');

      navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
          video.srcObject = stream;
          video.play();
          this.videoStarted = true;

          setInterval(() => {
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            canvas.toBlob(blob => this.detectLabels(blob), 'image/jpeg');
          }, 5000);
        })
        .catch(err => {
          console.error("Webcam error: ", err);
          this.error = "カメラのアクセスに失敗しました";
        });
    },
    async detectLabels(blob) {
      const reader = new FileReader();
      reader.onloadend = async () => {
        const base64data = reader.result.split(',')[1];
        const res = await fetch('https://vision.googleapis.com/v1/images:annotate?key=' + config.visionKey, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            requests: [{
              image: { content: base64data },
              features: [{ type: 'OBJECT_LOCALIZATION', maxResults: 10 }]
            }]
          })
        });
        const result = await res.json();
        const annotations = result.responses[0].localizedObjectAnnotations || [];
        this.boxes = annotations
          .filter(obj => obj.score > 0.6)
          .map(obj => {
            const v = obj.boundingPoly.normalizedVertices;
            return {
              label: obj.name,
              left: v[0].x * 640,
              top: v[0].y * 480,
              width: (v[1].x - v[0].x) * 640,
              height: (v[2].y - v[1].y) * 480
            };
          });
      };
      reader.readAsDataURL(blob);
    },
    async translateLabel(label) {
      const res = await fetch("https://api-free.deepl.com/v2/translate", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          auth_key: config.deeplKey,
          text: label,
          target_lang: "JA"
        })
      });
      const data = await res.json();
      this.translatedLabel = label + ' / ' + (data.translations?.[0]?.text || '翻訳失敗');
    },

    goToRanking() {
      window.location.href = 'ranking.html';
    }
  }
});