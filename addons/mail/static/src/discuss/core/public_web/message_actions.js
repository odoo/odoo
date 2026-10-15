import { registerMessageAction } from "@mail/core/common/message_actions";
import { _t } from "@web/core/l10n/translation";

registerMessageAction("create-or-view-thread", {
    condition: ({ message, channel }) =>
        message.channel_id?.eq(channel) && message.channel_id?.canCreateSubChannels,
    icon: "fa fa-comments-o",
    onSelected: async ({ message, store }) => {
        if (message.linkedSubChannel) {
            const subChannel = await store["discuss.channel"].getOrFetch(
                message.linkedSubChannel.id
            );
            subChannel?.open({ focus: true });
        } else {
            message.channel_id?.createSubChannel({ initialMessage: message });
        }
    },
    name: ({ message }) => (message.linkedSubChannel ? _t("View Thread") : _t("Create Thread")),
    sequence: 75,
});
