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
      this.mockDetectObjects();
    },
    retakePhoto() {
      this.photo = '';
      this.objects = [];
      this.jpResult = '';
      this.enResult = '';
      this.startCamera();
    },
    mockDetectObjects() {
      this.objects = [
        {
          name: "Bottle",
          boundingPoly: {
            normalizedVertices: [
              { x: 0.2, y: 0.2 },
              { x: 0.8, y: 0.2 },
              { x: 0.8, y: 0.8 },
              { x: 0.2, y: 0.8 }
            ]
          }
        }
      ];
      this.drawBoundingBoxes(this.objects);
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

        objects.forEach(obj => {
          const v = obj.boundingPoly.normalizedVertices;
          const x1 = v[0].x * canvas.width;
          const y1 = v[0].y * canvas.height;
          const x2 = v[2].x * canvas.width;
          const y2 = v[2].y * canvas.height;
          ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
        });

        ctx.setLineDash([]);
      };
      img.src = this.photo;
    },
    translateLabels() {
      const dict = { "Bottle": "ボトル", "Chair": "椅子" };
      const first = this.objects[0];
      const en = first.name;
      const jp = dict[en] || en + "（翻訳）";

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

