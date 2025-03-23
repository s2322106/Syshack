import config from './api-config.js';

export default {
  data() {
    return {
      videoStarted: false,
      boxes: [],
      translatedLabel: ''
    };
  },
  methods: {
    startCamera() {
      const video = this.$refs.video;
      const canvas = this.$refs.canvas;
      const ctx = canvas.getContext('2d');
      navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
          video.srcObject = stream;
          video.play();
          this.videoStarted = true;
          const interval = setInterval(() => {
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            canvas.toBlob(blob => this.detectLabels(blob), 'image/jpeg');
          }, 5000);
        });
    },
    async detectLabels(blob) {
      const reader = new FileReader();
      reader.onloadend = async () => {
        const base64data = reader.result.split(',')[1];
        const res = await fetch('https://vision.googleapis.com/v1/images:annotate?key=' + config.visionKey, {
          method: 'POST',
          body: JSON.stringify({
            requests: [{
              image: { content: base64data },
              features: [{ type: 'OBJECT_LOCALIZATION', maxResults: 10 }]
            }]
          }),
          headers: { 'Content-Type': 'application/json' }
        });
        const result = await res.json();
        const annotations = result.responses[0].localizedObjectAnnotations || [];
        this.boxes = annotations.map(obj => {
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
    }
  }
};