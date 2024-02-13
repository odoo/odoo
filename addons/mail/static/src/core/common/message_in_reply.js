/* @odoo-module */

import { Component, useState } from "@odoo/owl";

import { DEFAULT_AVATAR } from "@mail/core/common/persona_service";
import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";

export class MessageInReply extends Component {
    static props = ["message", "alignedRight", "onClick?"];
    static template = "mail.MessageInReply";

    setup() {
        this.store = useState(useService("mail.store"));
        this.threadService = useService("mail.thread");
    }

    get authorAvatarUrl() {
        if (
            this.props.message.message_type &&
            this.props.message.message_type.includes("email") &&
            !["partner", "guest"].includes(this.props.message.author?.type)
        ) {
            return url("/mail/static/src/img/email_icon.png");
        }

        if (this.props.message.parentMessage.author) {
            return this.props.message.parentMessage.author.avatarUrl;
        }

        return DEFAULT_AVATAR
    }
}
