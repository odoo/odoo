import { ACTION_TAGS } from "@mail/core/common/action";
import { registerThreadAction } from "@mail/core/common/thread_actions";
import { SubChannelList } from "@mail/discuss/core/public_web/sub_channel_list";
import { _t } from "@web/core/l10n/translation";

export const joinChannelAction = {
    condition: ({ channel, store }) =>
        channel &&
        !channel.self_member_id &&
        !["chat", "group"].includes(channel.channel_type) &&
        // The store falls back to a dummy guest, which cannot be added as a member.
        (store.self_user || store.self_guest?.id > 0),
    onSelected: ({ channel }) => channel.joinRpc(),
    icon: "login",
    name: _t("Join Channel"),
    sequence: 20,
    sequenceGroup: ({ ancestors }) => (ancestors.inDiscussContent ? undefined : 5),
    tags: [ACTION_TAGS.PRIMARY],
};
registerThreadAction("join-channel", joinChannelAction);
registerThreadAction("show-threads", {
    availableOffline: true,
    condition: ({ ancestors, channel }) =>
        (channel?.hasSubChannelFeature || channel?.parent_channel_id?.hasSubChannelFeature) &&
        !ancestors.inMessagingMenu,
    icon: "forum",
    name: _t("Threads"),
    panel: {
        component: SubChannelList,
        props: ({ channel }) => ({ channel: channel.parent_channel_id || channel }),
    },
    sequence: ({ ancestors }) => (ancestors.inChatWindow ? 40 : 5),
    sequenceGroup: 10,
});
