import { registerMessageAction } from "@mail/core/common/message_actions";
import { _t } from "@web/core/l10n/translation";

registerMessageAction("create-or-view-thread", {
    condition: ({ message, thread }) =>
        message.thread?.eq(thread) && message.channel_id?.canCreateSubChannels,
    icon: "fa fa-comments-o",
    onSelected: ({ message }) => {
        if (message.linkedSubChannel) {
            message.linkedSubChannel.open({ focus: true });
        } else {
            message.channel_id?.createSubChannel({ initialMessage: message });
        }
    },
    name: ({ message }) => (message.linkedSubChannel ? _t("View Thread") : _t("Create Thread")),
    sequence: 75,
});
