/* @odoo-module */

import { useRtc } from "@mail/new/rtc/rtc_hook";

import { Component } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class CallMenu extends Component {
    static props = [];
    static template = "mail.CallMenu";
    setup() {
        this.threadService = useService("mail.thread");
        this.rtc = useRtc();
    }
}

registry.category("systray").add("mail.CallMenu", { Component: CallMenu }, { sequence: 100 });
