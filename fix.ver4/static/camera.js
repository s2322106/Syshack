import config from '/static/api-config.js';
console.log("APIキー:", config.apiKey);

new Vue({
  el: '#app',
  data: {
    stream: null,
    photo: '',
    objects: [],
    jpResult: '',
    enResult: ''
  },
  methods: {
    startCamera() {
      navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
          this.stream = stream;
          this.$refs.video.srcObject = stream;
        })
        .catch(error => console.error("カメラ起動エラー:", error));
    },
    stopCamera() {
      if (this.stream) {
        this.stream.getTracks().forEach(track => track.stop());
        this.stream = null;
      }
    },
    capturePhoto() {
      const canvas = this.$refs.canvas;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(this.$refs.video, 0, 0, canvas.width, canvas.height);
      this.photo = canvas.toDataURL('image/png');
      this.stopCamera();
      this.detectObjects();  // ← Vision API 호출
    },
    retakePhoto() {
      this.photo = '';
      this.objects = [];
      this.jpResult = '';
      this.enResult = '';
      this.startCamera();
    },
    detectObjects() {
      fetch('/api/photo-analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: this.photo })
      })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            this.objects = data.objects;
            this.jpResult = data.jp;
            this.enResult = data.en;
            this.drawBoundingBoxes(this.objects);
          } else {
            alert(data.message || '認識に失敗しました');
          }
        })
        .catch(err => {
          console.error('API通信エラー:', err);
        });
    },
    drawBoundingBoxes(objects) {
      const canvas = this.$refs.canvas;
      const ctx = canvas.getContext('2d');
      const img = new Image();
      img.onload = () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

        ctx.setLineDash([6, 4]);
        ctx.strokeStyle = 'red';
        ctx.lineWidth = 2;
        ctx.font = '16px Arial';
        ctx.fillStyle = 'red';

        objects.forEach(obj => {
          const v = obj.boundingPoly.normalizedVertices;
          const x1 = v[0].x * canvas.width;
          const y1 = v[0].y * canvas.height;
          const x2 = v[2].x * canvas.width;
          const y2 = v[2].y * canvas.height;
          ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
          ctx.fillText(obj.name, x1, y1 - 5); // 객체 이름 표시
        });

        ctx.setLineDash([]);
      };
      img.src = this.photo;
    },
    goToMain() {
      window.location.href = "/main.html";
    },
    loadTranslationFromURL() {
      const params = new URLSearchParams(window.location.search);
      this.jpResult = params.get('jp') || '';
      this.enResult = params.get('en') || '';
    }
  },
  mounted() {
    this.startCamera();
    this.loadTranslationFromURL();
  },
  beforeDestroy() {
    this.stopCamera();
  }
});
