/* @odoo-module */

import { Component, useState } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class CallMenu extends Component {
    static props = [];
    static template = "discuss.CallMenu";
    setup() {
        this.threadService = useService("mail.thread");
        this.rtc = useState(useService("discuss.rtc"));
    }
}

registry.category("systray").add("discuss.CallMenu", { Component: CallMenu }, { sequence: 100 });
