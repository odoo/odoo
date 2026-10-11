import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";
import { useVoiceRecorder, VoiceRecorderAction } from "./voice_recorder";

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
    /** @type {import("@mail/core/common/action_list").GetActionComponent} */
    getActionComponent(params) {
        if (params.action.id === "voice-recording") {
            return VoiceRecorderAction;
        }
        return super.getActionComponent(params);
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
