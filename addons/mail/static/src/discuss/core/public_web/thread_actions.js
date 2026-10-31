import { useOnChange } from "@odoo/owl";

import { ACTION_TAGS } from "@mail/core/common/action";
import { registerThreadAction } from "@mail/core/common/thread_actions";
import { DiscussSideChannel } from "@mail/discuss/core/public_web/discuss_side_channel";
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
    sequenceGroup: ({ owner }) => (owner.isDiscussContent ? undefined : 5),
    tags: [ACTION_TAGS.PRIMARY],
};
registerThreadAction("join-channel", joinChannelAction);
registerThreadAction("show-threads", {
    availableOffline: true,
    condition: ({ channel, owner }) =>
        (channel?.hasSubChannelFeature || channel?.parent_channel_id?.hasSubChannelFeature) &&
        !owner.isDiscussSidebarChannelActions,
    icon: "forum",
    name: _t("Threads"),
    panel: {
        component: SubChannelList,
        props: ({ channel }) => ({ channel: channel.parent_channel_id || channel }),
    },
    sequence: ({ ancestors }) => (ancestors.inChatWindow ? 40 : 5),
    sequenceGroup: 10,
});
registerThreadAction("side-channel", {
    condition: ({ channel, store }) => store.discuss.sideChannel?.parent_channel_id?.eq(channel),
    hidden: true,
    panel: {
        component: DiscussSideChannel,
        onClose: ({ store }) => (store.discuss.sideChannel = undefined),
        props: ({ owner, store }) => ({
            channel: store.discuss.sideChannel,
            openInFullView: (panelAction) => owner.openSideChannelInFullView(panelAction),
        }),
    },
    setup: ({ action, actions, owner, store }) => {
        if (!owner.isDiscussContent) {
            return;
        }
        useOnChange(
            () => [store.discuss.sideChannel],
            (sideChannel) => {
                if (!sideChannel) {
                    action.closePanel();
                } else if (action.condition) {
                    action.openPanel({ keepPrevious: true });
                }
            }
        );
        useOnChange(
            () => [actions.panelAction],
            () => {
                // side channel is set but isn't on top, close the panel
                if (action.condition && !action.isActive) {
                    action.closePanel();
                }
            }
        );
    },
});
