import config from '/static/api-config.js';
console.log("APIキー:", config.apiKey);

new Vue({
  el: '#app',
  delimiters: ['[[', ']]'],
  data: {
    stream: null,
    photo: '',
    objects: [],
    jpResult: '',
    enResult: '',
    lastFrameData: null,
    stillStartTime: null,
    detectionCooldown: false,
    detectedNames: [],
    translatedObjects: []
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
          this.photo = reader.result;
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
            this.translateLabels();  // 번역 호출
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

      this.detectedNames = [];

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

          this.detectedNames.push(obj.name);
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
      this.detectedNames = [];
      this.translatedObjects = [];
      this.stillStartTime = null;
      this.startCamera();
    },
    async translateLabels() {
      if (!this.objects.length) return;

      const translations = await Promise.all(this.objects.map(async obj => {
        try {
          const res = await fetch("https://api-free.deepl.com/v2/translate", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({
              auth_key: config.deeplKey,
              text: obj.name,
              target_lang: "JA"
            })
          });

          const data = await res.json();

          if (!data.translations || !data.translations[0] || !data.translations[0].text) {
            alert(`「${obj.name}」の翻訳に失敗しました（API応答エラー）`);
            return { en: obj.name, jp: "翻訳失敗" };
          }

          return { en: obj.name, jp: data.translations[0].text };
        } catch (err) {
          console.error("DeepL通信エラー:", err);
          alert(`「${obj.name}」の翻訳中に通信エラーが発生しました`);
          return { en: obj.name, jp: "翻訳失敗" };
        }
      }));

      this.translatedObjects = translations;
    },
    goToMain() {
      window.location.href = "/main.html";
    }
  },
  mounted() {
    this.startCamera();
  },
  beforeDestroy() {
    this.stopCamera();
  }
});
