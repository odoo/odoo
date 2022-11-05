/** @odoo-module */

import { Component } from "@odoo/owl";
import { useMessaging } from "../messaging_hook";

export class CallUI extends Component {
    static template = "mail.call_ui";
    static props = ["thread", "compact?"];

    setup() {
        this.messaging = useMessaging();
    }

    disconnect() {
        this.messaging.stopCall(this.props.thread.id);
    }
}
