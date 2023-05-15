/** @odoo-module **/

import { CallInvitation } from "@mail/discuss/rtc/call_invitation";
import { useRtc } from "@mail/discuss/rtc/rtc_hook";
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class CallInvitations extends Component {
    static props = [];
    static components = { CallInvitation };
    static template = "mail.CallInvitations";

    setup() {
        this.rtc = useRtc();
        this.discussStore = useService("discuss.store");
    }
}

registry.category("main_components").add("CallInvitations", { Component: CallInvitations });
