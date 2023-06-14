/* @odoo-module */

import { openThread } from "@mail/core/common/thread_service";
import { useRtc } from "@mail/discuss/call/common/rtc_hook";

import { Component } from "@odoo/owl";

import { registry } from "@web/core/registry";

export class CallMenu extends Component {
    static props = [];
    static template = "discuss.CallMenu";
    setup() {
        this.rtc = useRtc();
        this.openThread = openThread;
    }
}

registry.category("systray").add("discuss.CallMenu", { Component: CallMenu }, { sequence: 100 });
