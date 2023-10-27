/* @odoo-module */

import { Component, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";

export class MessageInReply extends Component {
    static props = ["message", "alignedRight", "onClick?"];
    static template = "mail.MessageInReply";

    setup() {
        this.store = useState(useService("mail.store"));
        this.user = useService("user");
        this.threadService = useService("mail.thread");
    }

    get authorAvatarUrl() {
        if (
            this.message.type &&
            this.message.type.includes("email") &&
            !["partner", "guest"].includes(this.props.message.author?.type)
        ) {
            return url("/mail/static/src/img/email_icon.png");
        }
        return this.threadService.avatarUrl(
            this.message.parentMessage.author,
            this.props.message.parentMessage.originThread
        );
    }
}
