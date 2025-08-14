import { Component } from "@odoo/owl";

import { useCallActions } from "@mail/discuss/call/common/call_actions";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class CallMenu extends Component {
    static props = [];
    static template = "discuss.CallMenu";
    setup() {
        super.setup();
        this.rtc = useService("discuss.rtc");
        this.callActions = useCallActions({ thread: () => this.thread });
        this.isEnterprise = odoo.info && odoo.info.isEnterprise;
    }

    get icon() {
        const res = this.rtc.callActions.find(
            (action) => action.id === this.rtc.lastSelfCallAction
        )?.icon;
        return (typeof res === "function" ? res() : res) ?? "fa fa-microphone";
    }
}

registry.category("systray").add("discuss.CallMenu", { Component: CallMenu }, { sequence: 100 });
