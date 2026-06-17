import { Component, props, t } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class TalkingAudioBars extends Component {
    static template = "discuss.TalkingAudioBars";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = props({
            asPill: t.boolean().optional(false),
            session: t.instanceOf(this.store["discuss.channel.rtc.session"].Class),
        });
    }
}
