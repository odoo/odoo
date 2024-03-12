import { Component, useState } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class CallMenu extends Component {
    static props = [];
    static template = "discuss.CallMenu";
    setup() {
        super.setup();
        this.rtc = useState(useService("discuss.rtc"));
        this.store = useState(useService("mail.store"));
    }

    get rtcState() {
        return this.rtc.state.channel ? this.rtc.state : this.rtc.sharedState;
    }
    
    get rtcChannel() {
        let channel = this.rtcState.channel;
        if (!channel) {
            channel = this.store.Thread.get({
                model: "discuss.channel",
                id: this.rtcState.channelId
            });
        }
        return channel;
    }
}

registry.category("systray").add("discuss.CallMenu", { Component: CallMenu }, { sequence: 100 });
