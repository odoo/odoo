import { patch } from "@web/core/utils/patch";
import { HtmlComposer } from "@mail/core/web/html_composer";
import { useVoiceRecorder } from "../common/voice_recorder";

patch(HtmlComposer.prototype, {
    setup() {
        super.setup();
        this.voiceRecorder = useVoiceRecorder();
    },
    get isSendButtonDisabled() {
        return this.voiceRecording?.recording || super.isSendButtonDisabled;
    },
    onKeydown(ev) {
        if (ev.key === "Enter" && this.voiceRecording?.recording) {
            ev.preventDefault();
            return;
        }
        return super.onKeydown(ev);
    },
});
