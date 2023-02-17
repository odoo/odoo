/** @odoo-module **/

import { useStore } from "@mail/new/core/messaging_hook";
import { Component } from "@odoo/owl";
import { useRtc } from "@mail/new/rtc/rtc_hook";
import { registry } from "@web/core/registry";
import { CallInvitation } from "@mail/new/rtc/call_invitation";

export class CallInvitations extends Component {
    static props = [];
    static components = { CallInvitation };
    static template = "mail.call_invitations";

    setup() {
        this.rtc = useRtc();
        this.store = useStore();
    }
}

registry.category("main_components").add("CallInvitations", { Component: CallInvitations });
