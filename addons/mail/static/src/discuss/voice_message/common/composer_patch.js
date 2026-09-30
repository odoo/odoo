import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";
import { useVoiceRecorder } from "./voice_recorder";

patch(Composer, {
    components: { ...Composer.components },
});

patch(Composer.prototype, {
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
