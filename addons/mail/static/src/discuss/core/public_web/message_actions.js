import { registerMessageAction } from "@mail/core/common/message_actions";
import { _t } from "@web/core/l10n/translation";

registerMessageAction("create-or-view-thread", {
    condition: ({ message, store, thread }) =>
        message.thread?.eq(thread) &&
        message.thread.hasSubChannelFeature &&
        store.self.main_user_id?.share === false,
    icon: "fa fa-comments-o",
    onSelected: ({ message }) => {
        if (message.linkedSubChannel) {
            message.linkedSubChannel.open({ focus: true });
        } else {
            message.thread.createSubChannel({ initialMessage: message });
        }
    },
    name: ({ message }) => (message.linkedSubChannel ? _t("View Thread") : _t("Create Thread")),
    sequence: 75,
});
