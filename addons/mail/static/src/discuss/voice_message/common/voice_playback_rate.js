import { Component, types, useProps } from "@odoo/owl";

import { rotate } from "@web/core/utils/arrays";
import { useService } from "@web/core/utils/hooks";

export class VoicePlaybackRate extends Component {
    static template = "mail.VoicePlaybackRate";

    setup() {
        super.setup();
        this.playbackRates = [0.75, 1, 1.25, 1.5, 2];
        this.store = useService("mail.store");
        this.props = useProps({
            attachment: types.instanceOf(this.store["ir.attachment"]),
        });
    }

    cyclePlaybackRate() {
        const { voiceMetadata } = this.props.attachment;
        const currentIndex = this.playbackRates.indexOf(voiceMetadata.playbackRate);
        voiceMetadata.playbackRate = this.playbackRates[rotate(currentIndex, this.playbackRates)];
    }
}
