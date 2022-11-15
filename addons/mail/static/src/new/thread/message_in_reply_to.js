/** @odoo-module */

import { Component } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

import { useMessaging } from "@mail/new/messaging_hook";

export class MessageInReplyTo extends Component {
    setup() {
        this.messaging = useMessaging();
        this.user = useService("user");
    }

    get avatarUrl() {
        const parentMessage = this.props.message.parentMessage;
        if (
            parentMessage.author &&
            (parentMessage.resModel === "mail.channel" || !parentMessage.resModel)
        ) {
            return `/web/image/res.partner/${parentMessage.author.id}/avatar_128`;
        }
        if (parentMessage.author && parentMessage.resModel === "mail.channel") {
            return `/mail/channel/${parentMessage.resId}/partner/${parentMessage.author.id}/avatar_128`;
        }
        if (parentMessage.type === "email") {
            return "/mail/static/src/img/email_icon.png";
        }
        return "/mail/static/src/img/smiley/avatar.jpg";
    }
}

Object.assign(MessageInReplyTo, {
    props: ["message", "alignedRight", "onClick"],
    template: "mail.message_in_reply_to",
});
