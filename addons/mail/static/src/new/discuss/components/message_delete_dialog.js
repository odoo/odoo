/** @odoo-module **/

import { useMessaging } from "@mail/new/messaging_hook";

import { Component } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";

export class MessageDeleteDialog extends Component {
    setup() {
        this.messaging = useMessaging();
        this.title = this.env._t("Confirmation");
    }

    onClickDelete() {
        this.messaging.deleteMessage(this.props.message);
        this.props.close();
    }
}

Object.assign(MessageDeleteDialog, {
    components: { Dialog },
    props: ["close", "message", "messageComponent"],
    template: "mail.message.delete",
});
