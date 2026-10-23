import { registerMessageAction } from "@mail/core/common/message_actions";
import { MoveMessagesDialog } from "@mail/discuss/core/public_web/move_messages_dialog";
import { _t } from "@web/core/l10n/translation";

registerMessageAction("move-messages", {
    condition: ({ message, store, thread }) =>
        thread?.model === "discuss.channel" &&
        store.self_user?.share === false &&
        message.message_type === "comment",
    icon: "fa fa-arrows",
    name: _t("Move messages"),
    onSelected: ({ message, store, thread }) => {
        store.env.services.dialog.add(MoveMessagesDialog, { message, thread });
    },
    sequence: 105,
});
registerMessageAction("create-or-view-thread", {
    condition: ({ message, channel }) =>
        !message.isEmpty &&
        message.channel_id?.eq(channel) &&
        message.channel_id?.canCreateSubChannels,
    icon: "forum",
    onSelected: ({ message }) => {
        if (message.linkedSubChannel) {
            message.linkedSubChannel.open({ focus: true });
        } else {
            message.channel_id?.createSubChannel({ initialMessage: message });
        }
    },
    name: ({ message }) => (message.linkedSubChannel ? _t("View Thread") : _t("Create Thread")),
    sequence: 95,
});
