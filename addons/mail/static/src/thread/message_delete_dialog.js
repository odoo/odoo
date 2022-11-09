/** @odoo-module */

import { useMessaging } from "@mail/messaging_hook";
import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class MessageDeleteDialog extends Component {
    static template = "mail.message.delete";
    static components = { Dialog };
    static props = ["close", "message", "messageComponent"];

    setup() {
        this.messaging = useMessaging();
        this.title = this.env._t("Confirmation");
    }

    onClickDelete() {
        this.messaging.deleteMessage(this.props.message);
        this.props.close();
    }
}
