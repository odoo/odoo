import { useSubEnv } from "@web/owl2/utils";
import { ACTION_TAGS } from "@mail/core/common/action";
import { registerThreadAction } from "@mail/core/common/thread_actions";
import { SubChannelList } from "@mail/discuss/core/public_web/sub_channel_list";
import { attClassObjectToString } from "@mail/utils/common/format";
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
    btnAttrs: { "data-available-offline": true },
    condition: ({ channel, owner }) =>
        (channel?.hasSubChannelFeature || channel?.parent_channel_id?.hasSubChannelFeature) &&
        !owner.isDiscussSidebarChannelActions,
    icon: "forum",
    name: _t("Threads"),
    panel: {
        class: ({ owner, store }) =>
            attClassObjectToString({
                "o-mail-SubChannelList-panel": true,
                [store.discussDropdownMenuClass(owner)]: !owner.env.inMeetingView,
            }),
        component: SubChannelList,
        props: ({ channel }) => ({ channel: channel.parent_channel_id || channel }),
    },
    setup() {
        useSubEnv({ subChannelMenu: { open: () => this.openPanel() } });
    },
    sequence: ({ owner }) => (owner.props.chatWindow ? 40 : 5),
    sequenceGroup: 10,
});
