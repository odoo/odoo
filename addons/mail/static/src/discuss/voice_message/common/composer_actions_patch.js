import { registerComposerAction } from "@mail/core/common/composer_actions";
import { _t } from "@web/core/l10n/translation";
import { VoiceRecorder } from "./voice_recorder";

registerComposerAction("voice-start", {
    condition: ({ composer, voiceRecorder }) =>
        composer.targetThread?.channel &&
        voiceRecorder &&
        !voiceRecorder?.recording &&
        !composer.voiceAttachment,
    icon: "fa fa-microphone",
    name: _t("Voice Message"),
    onSelected: ({ voiceRecorder }) => voiceRecorder.onClick(),
    sequence: 10,
});
registerComposerAction("voice-recording", {
    component: VoiceRecorder,
    componentProps: ({ composer, voiceRecorder }) => ({ composer, state: voiceRecorder }),
    condition: ({ composer, voiceRecorder }) =>
        composer.targetThread?.channel && voiceRecorder?.recording,
    sequenceQuick: 10,
});
