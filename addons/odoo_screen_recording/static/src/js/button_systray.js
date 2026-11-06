/** @odoo-module **/
import SystrayMenu from 'web.SystrayMenu';
import Widget from 'web.Widget';
import rpc from 'web.rpc';
//Used to capture screen when button click according to selected screen

var ExampleWidget = Widget.extend({
   template: 'ScreenCaptureSystray',
   events: {
       'click #capture_screen': '_onClick',
   },
    async _onClick(){
      try {
       let stream = await navigator.mediaDevices.getDisplayMedia({
            video: true
        })
        let icon = document.querySelector(".record");
        icon.style.color = '#28a745';
        const mime = MediaRecorder.isTypeSupported("video/webm; codecs=vp9")
                 ? "video/webm; codecs=vp9"
                 : "video/webm"
        let mediaRecorder = new MediaRecorder(stream, {
            mimeType: mime
        })
        let chunks = []
        mediaRecorder.addEventListener('dataavailable', function(e) {
            chunks.push(e.data)
        })
        mediaRecorder.addEventListener('stop', function(){
        let icon = document.querySelector(".record");
        icon.style.color = 'white';
            let blob = new Blob(chunks, {
                type: chunks[0].type
            })
             const blobToBase64 = blob => {
              const reader = new FileReader();
              reader.readAsDataURL(blob);
              return new Promise(resolve => {
                reader.onloadend = () => {
                  resolve(reader.result);
                };
              });
            };
            blobToBase64(blob).then(res => {
              // res is base64 now
              rpc.query({
                  model: 'video.store',
                  method: 'video_record',
                  args: [res],
                  }).then(function(response){});
            });
        })
        mediaRecorder.start()
        } catch(e){}
    }
});
SystrayMenu.Items.push(ExampleWidget);
export default ExampleWidget;