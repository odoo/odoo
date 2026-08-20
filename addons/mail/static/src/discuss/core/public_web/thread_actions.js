import { useSubEnv } from "@web/owl2/utils";
import { ACTION_TAGS } from "@mail/core/common/action";
import { registerThreadAction } from "@mail/core/common/thread_actions";
import { SubChannelList } from "@mail/discuss/core/public_web/sub_channel_list";
import { attClassObjectToString } from "@mail/utils/common/format";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";

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
    actionPanelComponent: SubChannelList,
    actionPanelComponentProps: ({ channel }) => ({ channel: channel.parent_channel_id || channel }),
    actionPanelOpen({ rootRef }) {
        this.popover?.open(
            rootRef().querySelector(`[name="${this.id}"]`),
            this.actionPanelComponentProps
        );
    },
    actionPanelOuterClass: ({ owner, store }) =>
        attClassObjectToString({
            "o-mail-SubChannelList-panel": true,
            [store.discussDropdownMenuClass(owner)]: !owner.env.inMeetingView,
        }),
    btnAttrs: { "data-available-offline": true },
    condition: ({ channel, owner }) =>
        (channel?.hasSubChannelFeature || channel?.parent_channel_id?.hasSubChannelFeature) &&
        !owner.isDiscussSidebarChannelActions,
    icon: "forum",
    name: _t("Threads"),
    setup({ owner, store }) {
        if (owner.env.inDiscussApp && !store.env.services.ui.isSmall) {
            this.popover = usePopover(SubChannelList, {
                onClose: () => this.actionPanelClose(),
                fixedPosition: true,
                popoverClass: this.actionPanelOuterClass,
            });
        }
        useSubEnv({ subChannelMenu: { open: () => this.actionPanelOpen() } });
    },
    sequence: ({ owner }) => (owner.props.chatWindow ? 40 : 5),
    sequenceGroup: 10,
});
