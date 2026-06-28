import { registerComposerAction } from "@mail/core/common/composer_actions";
import { _t } from "@web/core/l10n/translation";
import { VoiceRecorder } from "./voice_recorder";

registerComposerAction("voice-start", {
    condition: ({ composer, owner }) =>
        composer.targetThread?.channel &&
        owner.voiceRecorder &&
        !owner.voiceRecorder?.recording &&
        !composer.voiceAttachment,
    icon: "fa fa-microphone",
    name: _t("Voice Message"),
    onSelected: ({ owner }) => owner.voiceRecorder.onClick(),
    sequence: 10,
});
registerComposerAction("voice-recording", {
    component: VoiceRecorder,
    componentProps: ({ composer, owner }) => ({ composer, state: owner.voiceRecorder }),
    condition: ({ composer, owner }) =>
        composer.targetThread?.channel && owner.voiceRecorder?.recording,
    sequenceQuick: 10,
});
