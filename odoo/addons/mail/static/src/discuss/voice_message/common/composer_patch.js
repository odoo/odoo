/* @odoo-module */

import { Composer } from "@mail/core/common/composer";
import { VoiceRecorder } from "@mail/discuss/voice_message/common/voice_recorder";
import { patch } from "@web/core/utils/patch";

patch(Composer, {
    components: { ...Composer.components, VoiceRecorder },
});

patch(Composer.prototype, {
    setup() {
        super.setup();
        this.state.recording = false;
    },
    get isSendButtonDisabled() {
        return this.state.recording || super.isSendButtonDisabled;
    },
    onKeydown(ev) {
        if (ev.key === "Enter" && this.state.recording) {
            ev.preventDefault();
            return;
        }
        return super.onKeydown(ev);
    },
});
