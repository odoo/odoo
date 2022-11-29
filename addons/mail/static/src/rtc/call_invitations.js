/** @odoo-module **/

import { useStore } from "@mail/core/messaging_hook";
import { Component } from "@odoo/owl";
import { useRtc } from "@mail/rtc/rtc_hook";
import { registry } from "@web/core/registry";
import { CallInvitation } from "@mail/rtc/call_invitation";

export class CallInvitations extends Component {
    static props = [];
    static components = { CallInvitation };
    static template = "mail.CallInvitations";

    setup() {
        this.rtc = useRtc();
        this.store = useStore();
    }
}

registry.category("main_components").add("CallInvitations", { Component: CallInvitations });
