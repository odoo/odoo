/* @odoo-module */

import { Component } from "@odoo/owl";
import { useRtc } from "@mail/new/rtc/rtc_hook";
import { useService } from "@web/core/utils/hooks";

export class CallMenu extends Component {
    // static components = { CallInviteRequestPopupList }; TODO
    static props = [];
    static template = "mail.call_menu";
    setup() {
        this.threadService = useService("mail.thread");
        this.rtc = useRtc();
    }
}
