import { registerComposerAction } from "@mail/core/common/composer_actions";
import { _t } from "@web/core/l10n/translation";

registerComposerAction("voice-start", {
    condition: ({ composer, voiceRecorder }) =>
        composer.targetThread?.channel &&
        voiceRecorder() &&
        !voiceRecorder().recording &&
        !composer.voiceAttachment,
    icon: "mic",
    name: _t("Voice Message"),
    onSelected: ({ voiceRecorder }) => voiceRecorder().onClick(),
    sequence: 10,
});
registerComposerAction("voice-recording", {
    condition: ({ composer, voiceRecorder }) =>
        composer.targetThread?.channel && voiceRecorder()?.recording,
    sequenceQuick: 10,
});
