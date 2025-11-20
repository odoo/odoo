import { messageActionsRegistry, registerMessageAction } from "@mail/core/common/message_actions";

import { toRaw } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";

registerMessageAction("set-new-message-separator", {
    condition: ({ message, thread }) =>
        thread &&
        thread.self_member_id &&
        thread.eq(message.thread) &&
        !message.hasNewMessageSeparator &&
        message.persistent,
    icon: "fa fa-eye-slash",
    name: _t("Mark as Unread"),
    onSelected: ({ message: msg }) => {
        const message = toRaw(msg);
        const selfMember = message.thread?.self_member_id;
        if (selfMember) {
            selfMember.new_message_separator = message.id;
            selfMember.new_message_separator_ui = selfMember.new_message_separator;
        }
        message.thread.markedAsUnread = true;
        rpc("/discuss/channel/set_new_message_separator", {
            channel_id: message.thread.id,
            message_id: message.id,
        });
    },
    sequence: 70,
});
registerMessageAction("view-replies", {
    condition: ({ message, owner }) =>
        owner.env.messageReplies &&
        message.child_ids_count &&
        !owner.env.messageReplies.message?.eq(message),
    icon: "fa fa-reply-all",
    name: _t("View Replies"),
    onSelected: ({ message, owner }) => {
        owner.env.messageReplies.open(message);
    },
    sequence: 104,
});

const replyToAction = messageActionsRegistry.get("reply-to");

patch(replyToAction, {
    onSelected({ owner }) {
        if (
            (owner.env.inChatWindow || owner.env.inMeetingView) &&
            owner.env.inMessageRepliesPanel
        ) {
            owner.env.messageReplies.close();
        }
        return super.onSelected(...arguments);
    },
});
