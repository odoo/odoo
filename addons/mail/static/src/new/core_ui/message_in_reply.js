/* @odoo-module */

import { Component } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

import { useMessaging, useStore } from "@mail/new/core/messaging_hook";
import { url } from "@web/core/utils/urls";

export class MessageInReply extends Component {
    static props = ["message", "alignedRight", "onClick"];
    static template = "mail.MessageInReply";

    setup() {
        this.messaging = useMessaging();
        this.store = useStore();
        this.user = useService("user");
        /** @type {import('@mail/new/core/thread_service').ThreadService} */
        this.threadService = useService("mail.thread");
    }

    get authorAvatarUrl() {
        if (
            this.message.type === "email" &&
            !["partner", "guest"].includes(this.props.message.author.type)
        ) {
            return url("/mail/static/src/img/email_icon.png");
        }
        return this.threadService.avatarUrl(this.message.author, this.props.message.originThread);
    }
}
