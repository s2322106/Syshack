import config from '/static/api-config.js';
console.log("APIキー:", config.apiKey);

new Vue({
  el: '#app',
  data: {
    stream: null,
    photo: '',
    objects: [],
    jpResult: '',
    enResult: '',
    lastFrameData: null,
    stillStartTime: null,
    detectionCooldown: false
  },
  methods: {
    startCamera() {
      navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
          this.stream = stream;
          this.$refs.video.srcObject = stream;
          this.setupAutoDetection();
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
      
      canvas.toBlob(blob => {
        const reader = new FileReader();
        reader.onloadend = () => {
          this.photo = reader.result;  // base64 URL
          this.stopCamera();
          this.sendToFlask(this.photo);
        };
        reader.readAsDataURL(blob);
      }, 'image/png');
    },
    sendToFlask(base64data) {
      fetch('/api/photo-analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: base64data })
      })
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            this.jpResult = data.jp;
            this.enResult = data.en;
            this.objects = data.objects;
            this.drawBoundingBoxes(this.objects);
          } else {
            alert("物体検出に失敗しました: " + data.message);
          }
        })
        .catch(err => {
          console.error("Flaskとの通信エラー:", err);
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
        ctx.font = '14px Arial';
        ctx.fillStyle = 'red';

        objects.forEach(obj => {
          const v = obj.boundingPoly.normalizedVertices;
          const x1 = v[0].x * canvas.width;
          const y1 = v[0].y * canvas.height;
          const x2 = v[2].x * canvas.width;
          const y2 = v[2].y * canvas.height;
          ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
          ctx.fillText(obj.name, x1 + 4, y1 - 6);
        });

        ctx.setLineDash([]);
      };

      img.src = this.photo;
    },
    setupAutoDetection() {
      const canvas = this.$refs.canvas;
      const ctx = canvas.getContext('2d');
      const video = this.$refs.video;

      setInterval(() => {
        if (!this.stream) return;
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const currentFrame = ctx.getImageData(0, 0, canvas.width, canvas.height);

        if (this.lastFrameData) {
          const diff = this.calculateFrameDifference(this.lastFrameData.data, currentFrame.data);
          const threshold = 0.02;
          const isStill = diff < threshold;

          if (isStill) {
            if (!this.stillStartTime) {
              this.stillStartTime = Date.now();
            } else if (Date.now() - this.stillStartTime > 1000 && !this.detectionCooldown && !this.photo) {
              // 자동 인식 트리거 (사진 상태가 아닐 때만)
              canvas.toBlob(blob => {
                const reader = new FileReader();
                reader.onloadend = () => {
                  this.photo = reader.result;
                  this.stopCamera();
                  this.sendToFlask(this.photo);
                };
                reader.readAsDataURL(blob);
              }, 'image/jpeg');

              this.detectionCooldown = true;
              setTimeout(() => {
                this.detectionCooldown = false;
              }, 3000);
            }
          } else {
            this.stillStartTime = null;
          }
        }

        this.lastFrameData = currentFrame;
      }, 200);
    },
    calculateFrameDifference(data1, data2) {
      let diffPixels = 0;
      for (let i = 0; i < data1.length; i += 4) {
        const rDiff = Math.abs(data1[i] - data2[i]);
        const gDiff = Math.abs(data1[i + 1] - data2[i + 1]);
        const bDiff = Math.abs(data1[i + 2] - data2[i + 2]);
        if (rDiff + gDiff + bDiff > 30) diffPixels++;
      }
      return diffPixels / (data1.length / 4);
    },
    retakePhoto() {
      this.photo = '';
      this.objects = [];
      this.jpResult = '';
      this.enResult = '';
      this.stillStartTime = null;
      this.startCamera();
    },
    translateLabels() {
      const first = this.objects[0];
      const en = first.name;
      const jp = this.jpResult || en + "（翻訳）";
      const params = new URLSearchParams({ en, jp });
      window.location.href = `/camera?${params.toString()}`;
    },
    loadTranslationFromURL() {
      const params = new URLSearchParams(window.location.search);
      this.jpResult = params.get('jp') || '';
      this.enResult = params.get('en') || '';
    },
    goToMain() {
      window.location.href = "/main.html";
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
