import { registerComposerAction } from "@mail/core/common/composer_actions";
import { Component, xml } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

registerComposerAction("voice-start", {
    condition: ({ composer, owner }) =>
        composer.targetThread?.model === "discuss.channel" &&
        owner.voiceRecorder &&
        !owner.voiceRecorder?.recording &&
        !composer.voiceAttachment,
    icon: "fa fa-microphone",
    name: _t("Voice Message"),
    onSelected: ({ owner }) => owner.voiceRecorder.onClick(),
    sequence: 10,
});
registerComposerAction("voice-stop", {
    condition: ({ composer, owner }) =>
        composer.targetThread?.model === "discuss.channel" && owner.voiceRecorder?.recording,
    icon: "fa fa-circle text-danger o-mail-VoiceRecorder-dot",
    name: _t("Stop Recording"),
    onSelected: ({ owner }) => owner.voiceRecorder.onClick(),
    sequence: 10,
});
registerComposerAction("voice-recording", {
    component: class VoiceMessageRecordingButton extends Component {
        static props = ["composer", "state"];
        static template = xml`
            <button class="o-mail-VoiceRecorder d-flex align-items-center btn border-0 o-recording rounded-start-0 rounded-end user-select-none p-0" t-att-title="title" t-att-disabled="props.state.isActionPending or props.composer.voiceAttachment" t-on-click="props.state.onClick">
                <div class="o-mail-VoiceRecorder-elapsed o-active recording ms-2 me-1" t-att-class="{ 'text-danger': props.state.limitWarning }" style="font-variant-numeric: tabular-nums;">
                    <span class="d-flex text-truncate" t-esc="props.state.elapsed"/>
                </div>
                <span class="rounded-circle p-1"><i class="fa fa-fw fa-circle text-danger o-mail-VoiceRecorder-dot"/></span>
            </button>
        `;
        get title() {
            return _t("Stop Recording");
        }
    },
    componentProps: ({ composer, owner }) => ({ composer, state: owner.voiceRecorder }),
    condition: ({ composer, owner }) =>
        composer.targetThread?.model === "discuss.channel" && owner.voiceRecorder?.recording,
    sequenceQuick: 10,
});
