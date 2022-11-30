/** @odoo-module **/

import { useMessaging } from "@mail/new/messaging_hook";

import { Component } from "@odoo/owl";

export class CallSettings extends Component {
    setup() {
        this.messaging = useMessaging();
    }
}

Object.assign(CallSettings, {
    template: "mail.settings",
});
