import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";
import { useVoiceRecorder, VoiceRecorder, VoiceRecorderAction } from "./voice_recorder";

patch(Composer, {
    components: { ...Composer.components, VoiceRecorder },
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
    showVoiceRecorderAbove() {
        return this.compact || this.ancestors.inMeetingView || this.ui.isSmall();
    },
    get isSendButtonDisabled() {
        if (!this.voiceRecorder?.recording) {
            return super.isSendButtonDisabled;
        }
        return (
            !this.state.active ||
            this.voiceRecorder.isActionPending ||
            this.props.composer().attachments.some(({ uploading }) => uploading)
        );
    },
    onKeydown(ev) {
        if (
            ev.key === "Escape" &&
            this.voiceRecorder?.recording &&
            !document.querySelector(".o-we-SuggestionList .o-navigable")
        ) {
            ev.preventDefault();
            ev.stopPropagation();
            this.voiceRecorder.cancelRecording();
            return;
        }
        return super.onKeydown(ev);
    },
    async editMessage() {
        if (this.voiceRecorder?.recording && !(await this.stopVoiceRecording())) {
            return;
        }
        return super.editMessage();
    },
    async sendMessage() {
        if (this.voiceRecorder?.recording && !(await this.stopVoiceRecording())) {
            return;
        }
        return super.sendMessage();
    },
    /** @returns {Promise<boolean>} whether the recording was attached to the composer */
    async stopVoiceRecording() {
        return !this.isSendButtonDisabled && Boolean(await this.voiceRecorder.stopRecording());
    },
});
