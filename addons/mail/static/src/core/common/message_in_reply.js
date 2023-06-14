/* @odoo-module */

import { useMessaging, useStore } from "@mail/core/common/messaging_hook";
import { avatarUrl } from "@mail/core/common/thread_service";

import { Component } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";

export class MessageInReply extends Component {
    static props = ["message", "alignedRight", "onClick?"];
    static template = "mail.MessageInReply";

    setup() {
        this.messaging = useMessaging();
        this.store = useStore();
        this.user = useService("user");
    }

    get authorAvatarUrl() {
        if (
            this.message.type === "email" &&
            !["partner", "guest"].includes(this.props.message.author.type)
        ) {
            return url("/mail/static/src/img/email_icon.png");
        }
        return avatarUrl(
            this.message.parentMessage.author,
            this.props.message.parentMessage.originThread
        );
    }
}
