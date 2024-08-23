import { Composer } from "@mail/core/common/composer";
import { VoiceRecorder } from "@mail/discuss/voice_message/common/voice_recorder";
import { patch } from "@web/core/utils/patch";

patch(Composer, {
    components: { ...Composer.components, VoiceRecorder },
});

patch(Composer.prototype, {
    get isSendButtonDisabled() {
        return this.recordingState.recording || super.isSendButtonDisabled;
    },
    onKeydown(ev) {
        if (ev.key === "Enter" && this.recordingState.recording) {
            ev.preventDefault();
            return;
        }
        return super.onKeydown(ev);
    },
});
