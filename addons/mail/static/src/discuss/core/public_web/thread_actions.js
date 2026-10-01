import { useSubEnv } from "@web/owl2/utils";
import { ACTION_TAGS } from "@mail/core/common/action";
import { registerThreadAction, ThreadAction } from "@mail/core/common/thread_actions";
import { SubChannelList } from "@mail/discuss/core/public_web/sub_channel_list";
import { attClassObjectToString } from "@mail/utils/common/format";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { patch } from "@web/core/utils/patch";

const SIDE_CHANNEL_ACTIONS = [
    "notification-settings",
    "join-channel",
    "open-thread",
    "close-side-channel",
];

patch(ThreadAction.prototype, {
    _condition({ action, channel, owner }) {
        if (
            owner.isDiscussContent &&
            channel?.discussAppAsSideChannel &&
            !SIDE_CHANNEL_ACTIONS.includes(action.id)
        ) {
            return false;
        }
        return super._condition(...arguments);
    },
    actionPanelOpen() {
        const { store } = this.params;
        if (this.actionPanelComponent && !this.popover) {
            store.discuss.sideChannel = undefined;
        }
        return super.actionPanelOpen(...arguments);
    },
});

registerThreadAction("open-thread", {
    condition: ({ channel, owner }) => owner.isDiscussContent && channel?.discussAppAsSideChannel,
    icon: "expand_content",
    name: _t("Open in Full View"),
    onSelected: ({ channel }) => channel.open({ focus: true }),
    sequence: 10,
    sequenceGroup: 5,
});

registerThreadAction("close-side-channel", {
    condition: ({ channel, owner }) => owner.isDiscussContent && channel?.discussAppAsSideChannel,
    icon: "close_small",
    name: _t("Close"),
    onSelected: ({ store }) => (store.discuss.sideChannel = undefined),
    sequence: 10,
    sequenceGroup: 1,
});

export const joinChannelAction = {
    condition: ({ channel, store }) =>
        channel &&
        !channel.self_member_id &&
        !["chat", "group"].includes(channel.channel_type) &&
        // The store falls back to a dummy guest, which cannot be added as a member.
        (store.self_user || store.self_guest?.id > 0),
    onSelected: ({ channel }) => channel.joinRpc(),
    icon: "login",
    name: ({ channel }) => (channel.parent_channel_id ? _t("Join Thread") : _t("Join Channel")),
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
