/* @odoo-module */

import { Composer } from "@mail/core/common/composer";
import { VoiceRecorder } from "@mail/discuss/voice_message/common/voice_recorder";
import { patch } from "@web/core/utils/patch";

patch(Composer, "discuss/voice_message/common", {
    components: { ...Composer.components, VoiceRecorder },
});

patch(Composer.prototype, "discuss/core/common", {
    setup() {
        this._super();
        this.onchangeRecording = this.onchangeRecording.bind(this);
        this.tempRecorderId = 0;
    },
    prepareStateParameters() {
        const stateParameters = this._super();
        stateParameters.recording = false;
        return stateParameters;
    },
    async sendMessage() {
        this._super();
        this.tempRecorderId += 1;
        this.props.composer.hasVoice = false;
    },
    get isSendButtonDisabled() {
        return this.state.recording || this._super();
    },
    onchangeRecording() {
        this.state.recording = !this.state.recording;
    },
});
