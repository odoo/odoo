/** @odoo-module **/

import { useStore } from "@mail/new/core/messaging_hook";
import { Component } from "@odoo/owl";
import { useRtc } from "@mail/new/rtc/rtc_hook";
import { registry } from "@web/core/registry";
import { CallInviteRequestPopup } from "@mail/new/rtc/call_invite_request_popup";

export class CallInviteRequestPopupList extends Component {
    static props = [];
    static components = { CallInviteRequestPopup };
    static template = "mail.call_invite_request_popup_list";

    setup() {
        this.rtc = useRtc();
        this.store = useStore();
    }
}

registry.category("main_components").add("CallInvitations", {
    Component: CallInviteRequestPopupList,
});
