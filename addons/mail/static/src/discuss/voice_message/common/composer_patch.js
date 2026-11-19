import { CircleInlineAction } from "@mail/core/common/action_list";
import { Composer } from "@mail/core/common/composer";
import { DICTATION_STATE, isDictationSupported } from "@mail/core/common/dictation/dictation_hook";
import { usePressAndHold } from "@mail/utils/common/hooks";
import { patch } from "@web/core/utils/patch";
import { useVoiceRecorder, VoiceRecorderAction } from "./voice_recorder";

class QuickVoiceStartInlineAction extends CircleInlineAction {
    get classObj() {
        return { ...super.classObj, "o-sendMessageActive o-text-white shadow-sm": true };
    }
}

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
        if (isDictationSupported()) {
            // a click on the voice button records a voice message, holding it dictates a text
            usePressAndHold(this.inputContainerRef, {
                onHold: () => this.startDictation(),
                onRelease: () => this.dictation.stop(),
                predicate: (ev) =>
                    Boolean(ev.target.closest("button[name='voice-start']")) && this.canDictate(),
            });
        }
    },
    /** @type {import("@mail/core/common/action_list").GetActionComponent} */
    getActionComponent(params) {
        if (params.action.id === "voice-recording") {
            return VoiceRecorderAction;
        }
        if (params.action.id === "voice-start" && params.inline && this.showQuickVoiceStart) {
            return QuickVoiceStartInlineAction;
        }
        return super.getActionComponent(params);
    },
    get showQuickVoiceStart() {
        const composer = this.props.composer;
        return Boolean(
            composer.targetThread?.channel &&
                this.voiceRecorder &&
                !this.voiceRecorder.recording &&
                !composer.voiceAttachment &&
                // kept while the dictated text fills the composer, as it is held
                (this.isEmpty || this.dictation.state() !== DICTATION_STATE.IDLE)
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
