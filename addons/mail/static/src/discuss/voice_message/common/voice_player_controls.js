import { Component, types, useProps } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class VoicePlayerControls extends Component {
    static template = "mail.VoicePlayerControls";

    setup() {
        super.setup();
        this.playbackRates = [0.75, 1, 1.25, 1.5, 2];
        this.store = useService("mail.store");
        this.props = useProps({
            attachment: types.instanceOf(this.store["ir.attachment"]),
        });
        /** @type {import("@mail/discuss/voice_message/common/voice_message_service").VoiceMessageService} */
        this.voiceMessageService = useService("discuss.voice_message");
    }

    get activePlayer() {
        const player = this.voiceMessageService.activePlayer;
        return player?.props.attachment.eq(this.props.attachment) ? player : null;
    }

    get playbackRate() {
        return this.props.attachment.voiceMetadata.playbackRate;
    }

    cyclePlaybackRate() {
        const currentIndex = this.playbackRates.indexOf(this.playbackRate);
        const nextIndex = (currentIndex + 1) % this.playbackRates.length;
        this.props.attachment.voiceMetadata.playbackRate = this.playbackRates[nextIndex];
        this.activePlayer?.applySettings();
    }
}
