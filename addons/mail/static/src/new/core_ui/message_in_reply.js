/* @odoo-module */

import { Component } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

import { useMessaging, useStore } from "@mail/new/core/messaging_hook";

export class MessageInReply extends Component {
    static props = ["message", "alignedRight", "onClick"];
    static template = "mail.MessageInReply";

    setup() {
        this.messaging = useMessaging();
        this.store = useStore();
        this.user = useService("user");
    }
}
