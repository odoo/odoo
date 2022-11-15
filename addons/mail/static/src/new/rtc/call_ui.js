/** @odoo-module */

import { Component } from "@odoo/owl";
import { useMessaging } from "../messaging_hook";

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
