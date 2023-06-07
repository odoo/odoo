/* @odoo-module */

import { useStore } from "@mail/core/messaging_hook";
import { CallInvitation } from "@mail/discuss/call/call_invitation";
import { useRtc } from "@mail/discuss/call/rtc_hook";
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class CallInvitations extends Component {
    static props = [];
    static components = { CallInvitation };
    static template = "discuss.CallInvitations";

    setup() {
        this.rtc = useRtc();
        this.store = useStore();
    }
}

registry.category("main_components").add("discuss.CallInvitations", { Component: CallInvitations });
