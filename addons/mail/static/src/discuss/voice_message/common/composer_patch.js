import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";
import { useVoiceRecorder } from "./voice_recorder";

patch(Composer, {
    components: { ...Composer.components },
});

patch(Composer.prototype, {
    setup() {
        super.setup();
        this.voiceRecorder = useVoiceRecorder(
            { onRecordReady: (file) => this.attachmentUploader.uploadFile(file, { voice: true }) },
            { rootRef: this.rootRef }
        );
    },
    get showQuickVoiceStart() {
        const composer = this.props.composer;
        return Boolean(
            composer.targetThread?.channel &&
                this.voiceRecorder &&
                !this.voiceRecorder.recording &&
                !composer.voiceAttachment &&
                this.isEmpty
        );
    },
    get isSendButtonHidden() {
        return this.showQuickVoiceStart || super.isSendButtonHidden;
    },
    get isSendButtonDisabled() {
        return this.voiceRecorder?.recording || super.isSendButtonDisabled;
    },
    onKeydown(ev) {
        if (ev.key === "Enter" && this.voiceRecorder?.recording) {
            ev.preventDefault();
            return;
        }
        return super.onKeydown(ev);
    },
});
