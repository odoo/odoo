// @ts-check
/** @odoo-module native */
import { registerComposerAction } from "@mail/core/common/composer_actions";
import { Component, xml } from "@odoo/owl";
import { _t } from "@web/core/translation";

/** @typedef {import("@mail/core/common/composer_actions").ActionParams} ActionParams */
registerComposerAction("voice-start", {
    /** @param {ActionParams} params */
    condition: ({ composer, owner }) =>
        composer.targetThread?.isChannelKind &&
        owner.voiceRecorder &&
        !owner.voiceRecorder?.recording &&
        !composer.voiceAttachment,
    icon: "fa-solid fa-microphone",
    name: _t("Voice Message"),
    /** @param {ActionParams} params */
    onSelected: ({ owner }) => owner.voiceRecorder.onClick(),
    sequence: 10,
});
registerComposerAction("voice-stop", {
    /** @param {ActionParams} params */
    condition: ({ composer, owner }) =>
        composer.targetThread?.isChannelKind && owner.voiceRecorder?.recording,
    icon: "fa-solid fa-circle text-danger o-mail-VoiceRecorder-dot",
    name: _t("Stop Recording"),
    /** @param {ActionParams} params */
    onSelected: ({ owner }) => owner.voiceRecorder.onClick(),
    sequence: 10,
});
registerComposerAction("voice-recording", {
    component: class VoiceMessageRecordingButton extends Component {
        static props = ["composer", "state"];
        static template = xml`
            <button class="o-mail-VoiceRecorder d-flex align-items-center btn border-0 o-recording rounded-start-0 rounded-end user-select-none p-0" t-att-title="this.title" t-att-disabled="this.props.state.isActionPending or this.props.composer.voiceAttachment" t-on-click="this.props.state.onClick">
                <div class="o-mail-VoiceRecorder-elapsed o-active recording ms-2 me-1" t-att-class="{ 'text-danger': this.props.state.limitWarning }" style="font-variant-numeric: tabular-nums;">
                    <span class="d-flex text-truncate" t-out="this.props.state.elapsed"/>
                </div>
                <span class="rounded-circle p-1"><i class="fa-solid fa-circle text-danger o-mail-VoiceRecorder-dot"/></span>
            </button>
        `;
        get title() {
            return _t("Stop Recording");
        }
    },
    /** @param {ActionParams} params */
    componentProps: ({ composer, owner }) => ({ composer, state: owner.voiceRecorder }),
    /** @param {ActionParams} params */
    condition: ({ composer, owner }) =>
        composer.targetThread?.isChannelKind && owner.voiceRecorder?.recording,
    sequenceQuick: 10,
});
