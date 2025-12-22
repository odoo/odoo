import { Component, useState } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { callActionsRegistry, useCallActions } from "./call_actions";

export class CallMenu extends Component {
    static props = [];
    static template = "discuss.CallMenu";
    setup() {
        super.setup();
        this.rtc = useState(useService("discuss.rtc"));
        this.callActions = useCallActions();
        this.isEnterprise = odoo.info && odoo.info.isEnterprise;
    }

    get icon() {
        return (
            callActionsRegistry.get(this.rtc.lastSelfCallAction, undefined)?.icon ?? "fa-microphone"
        );
    }
}

registry.category("systray").add("discuss.CallMenu", { Component: CallMenu }, { sequence: 100 });
