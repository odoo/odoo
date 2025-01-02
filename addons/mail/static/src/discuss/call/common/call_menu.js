import { Component } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { callActionsRegistry, useCallActions } from "./call_actions";

export class CallMenu extends Component {
    static props = [];
    static template = "discuss.CallMenu";
    setup() {
        super.setup();
        this.rtc = useService("discuss.rtc");
        this.callActions = useCallActions();
    }

    get icon() {
        return (
            callActionsRegistry.get(this.rtc.lastSelfCallAction, undefined)?.icon ?? "fa-microphone"
        );
    }
}

registry.category("systray").add("discuss.CallMenu", { Component: CallMenu }, { sequence: 100 });
