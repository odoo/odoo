/** @odoo-module **/

import { useMessaging } from "@mail/new/messaging_hook";

import { Component } from "@odoo/owl";

export class CallUI extends Component {
    setup() {
        this.messaging = useMessaging();
    }

    disconnect() {
        this.messaging.stopCall(this.props.thread.id);
    }
}

Object.assign(CallUI, {
    props: ["thread", "compact?"],
    template: "mail.call_ui",
});
