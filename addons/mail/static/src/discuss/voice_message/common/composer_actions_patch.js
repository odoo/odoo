import { registerComposerAction } from "@mail/core/common/composer_actions";
import { _t } from "@web/core/l10n/translation";
import { VoiceRecorder } from "./voice_recorder";
import { ACTION_TAGS } from "@mail/core/common/action";

registerComposerAction("voice-start", {
    btnClass: ({ owner }) =>
        owner.showQuickVoiceStart ? "o-sendMessageActive o-text-white shadow-sm" : "",
    condition: ({ composer, owner }) =>
        composer.targetThread?.channel &&
        owner.voiceRecorder &&
        !owner.voiceRecorder?.recording &&
        !composer.voiceAttachment,
    icon: "mic",
    name: _t("Voice Message"),
    onSelected: ({ owner }) => owner.voiceRecorder.onClick(),
    sequence: 10,
    sequenceQuick: ({ owner }) => (owner.showQuickVoiceStart ? 35 : undefined),
    tags: ({ owner }) => (owner.showQuickVoiceStart ? ACTION_TAGS.PRIMARY : undefined),
});
registerComposerAction("voice-recording", {
    component: VoiceRecorder,
    componentProps: ({ composer, owner }) => ({ composer, state: owner.voiceRecorder }),
    condition: ({ composer, owner }) =>
        composer.targetThread?.channel && owner.voiceRecorder?.recording,
    sequenceQuick: 10,
});
