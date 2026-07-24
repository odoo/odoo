import { useChildSubEnv } from "@web/owl2/utils";
import { ACTION_TAGS } from "@mail/core/common/action";
import { registerThreadAction } from "@mail/core/common/thread_actions";
import { AttachmentPanel } from "@mail/discuss/core/common/attachment_panel";
import { ChannelActionDialog } from "@mail/discuss/core/common/channel_action_dialog";
import { ChannelInvitation } from "@mail/discuss/core/common/channel_invitation";
import { ChannelMemberList } from "@mail/discuss/core/common/channel_member_list";
import { DeleteThreadDialog } from "@mail/discuss/core/common/delete_thread_dialog";
import { NotificationSettings } from "@mail/discuss/core/common/notification_settings";
import { PinnedMessagesPanel } from "@mail/discuss/core/common/pinned_messages_panel";

import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";

registerThreadAction("pinned-messages", {
    actionPanelComponent: PinnedMessagesPanel,
    actionPanelComponentProps: ({ channel }) => ({ channel }),
    actionPanelOuterClass: "o-discuss-PinnedMessagesPanel bg-inherit",
    btnAttrs: { "data-available-offline": true },
    condition: ({ channel, chatWindow, isDiscussSidebarChannelActions }) =>
        channel && (!chatWindow || chatWindow.isOpen) && !isDiscussSidebarChannelActions,
    icon: "fa fa-fw fa-thumb-tack",
    name: ({ action }) => (action.isActive ? _t("Hide Pinned Messages") : _t("Pinned Messages")),
    sequence: 20,
    sequenceGroup: 10,
    setup() {
        useChildSubEnv({
            pinMenu: {
                open: () => this.actionPanelOpen({ keepPrevious: true }),
                close: () => {
                    if (this.isActive) {
                        this.actionPanelClose();
                    }
                },
            },
        });
    },
});
registerThreadAction("add-to-favorites", {
    /**
     * @param {Object} param0
     * @param {import("models").DiscussChannel} param0.channel
     */
    condition: ({ channel, isDiscussContent, store }) =>
        store.self_user?.share === false &&
        channel &&
        channel.self_member_id &&
        !channel.self_member_id.is_favorite &&
        (!isDiscussContent || channel.showFavoriteActionsInHeader),
    icon: "fa fa-fw fa-star",
    name: _t("Add to Favorites"),
    /**
     * @param {Object} param0
     * @param {import("models").DiscussChannel} param0.channel
     * @param {import("models").Store} param0.store
     */
    onSelected: async ({ channel, inDiscussApp, store }) => {
        store.fetchStoreData(
            "/discuss/channel/favorite",
            { channel_id: channel.id, is_favorite: true },
            { silent: false }
        );
        if (inDiscussApp && !store.env.services.ui.isSmall) {
            return;
        }
        store.env.services.notification.add(
            _t("Added %(name)s to Favorites", { name: channel.displayName }),
            { type: "success" }
        );
    },
    sequence: 40,
    sequenceGroup: 20,
});
registerThreadAction("remove-from-favorites", {
    /**
     * @param {Object} param0
     * @param {import("models").DiscussChannel} param0.channel
     */
    condition: ({ channel, isDiscussContent }) =>
        channel?.self_member_id?.is_favorite &&
        (!isDiscussContent || channel.showFavoriteActionsInHeader),
    icon: "fa fa-fw fa-star-o",
    name: _t("Remove from Favorites"),
    /**
     * @param {Object} param0
     * @param {import("models").DiscussChannel} param0.channel
     * @param {import("models").Store} param0.store
     */
    onSelected: async ({ channel, inDiscussApp, store }) => {
        store.fetchStoreData(
            "/discuss/channel/favorite",
            { channel_id: channel.id, is_favorite: false },
            { silent: false }
        );
        if (inDiscussApp && !store.env.services.ui.isSmall) {
            return;
        }
        store.env.services.notification.add(
            _t("Removed %(name)s from Favorites", { name: channel.displayName }),
            { type: "warning" }
        );
    },
    sequence: 40,
    sequenceGroup: 20,
});
registerThreadAction("notification-settings", {
    actionPanelComponent: NotificationSettings,
    actionPanelComponentProps: ({ channel }) => ({ channel }),
    actionPanelOpen({ isDiscussContent, rootRef }) {
        if (isDiscussContent) {
            this.popover?.open(
                rootRef().querySelector(`[name="${this.id}"]`),
                this.actionPanelComponentProps
            );
        }
    },
    actionPanelOuterClass: ({ discussDropdownMenuClass }) => discussDropdownMenuClass,
    dropdown: ({ isDiscussContent }) => !isDiscussContent,
    dropdownComponent: NotificationSettings,
    dropdownComponentProps: ({ channel }) => ({ channel }),
    condition: ({ channel, chatWindow, store }) =>
        channel && store.self_user && (!chatWindow || chatWindow.isOpen),
    setup({ chatWindow }) {
        if (!chatWindow) {
            this.popover = usePopover(NotificationSettings, {
                onClose: () => this.actionPanelClose(),
                position: "bottom-end",
                fixedPosition: true,
                popoverClass: this.actionPanelOuterClass,
            });
        }
    },
    icon: ({ channel }) =>
        channel?.self_member_id?.mute_until_dt
            ? "fa fa-fw text-danger fa-bell-slash"
            : "fa fa-fw fa-bell",
    name: ({ channel }) =>
        channel.channel_type == "channel" ? _t("Notification Settings") : _t("Mute Conversation"),
    sequence: 10,
    sequenceGroup: 30,
});
registerThreadAction("attachments", {
    actionPanelComponent: AttachmentPanel,
    actionPanelComponentProps: ({ channel }) => ({ channel }),
    btnAttrs: { "data-available-offline": true },
    condition: ({ channel, chatWindow, isDiscussSidebarChannelActions }) =>
        channel?.hasAttachmentPanel &&
        (!chatWindow || chatWindow.isOpen) &&
        !isDiscussSidebarChannelActions,
    icon: "fa fa-fw fa-paperclip",
    name: _t("Attachments"),
    sequence: 10,
    sequenceGroup: 10,
});
registerThreadAction("invite-people", {
    actionPanelComponent: ChannelInvitation,
    actionPanelComponentProps: ({ channel }) => ({ channel }),
    actionPanelOpen({ channel, inMeetingView, isDiscussSidebarChannelActions, rootRef, store }) {
        if (isDiscussSidebarChannelActions) {
            store.env.services.dialog?.add(ChannelActionDialog, {
                title: channel.displayName,
                contentComponent: ChannelInvitation,
                contentProps: {
                    channel,
                    close: () => store.env.services.dialog.closeAll(),
                },
            });
        } else if (!inMeetingView) {
            this.popover?.open(
                rootRef().querySelector(`[name="${this.id}"]`),
                this.actionPanelComponentProps
            );
        }
    },
    actionPanelOuterClass: ({ chatWindow, discussDropdownMenuClass, inMeetingView }) =>
        `o-discuss-ChannelInvitation ${chatWindow ? "bg-inherit" : ""} border border-secondary ${
            inMeetingView ? "" : discussDropdownMenuClass
        }`,
    condition: ({ channel, chatWindow, isDiscussContent, pipWindow }) =>
        channel &&
        !pipWindow &&
        (!chatWindow || chatWindow.isOpen) &&
        !(isDiscussContent && channel?.hasMemberList),
    icon: "oi oi-fw oi-user-plus",
    name: _t("Invite People"),
    sequence: 20,
    sequenceGroup: ({ isDiscussContent }) => (isDiscussContent ? 10 : 20),
    setup({ chatWindow, inMeetingView }) {
        if (!chatWindow && !inMeetingView) {
            this.popover = usePopover(ChannelInvitation, {
                onClose: () => this.actionPanelClose(),
                popoverClass: this.actionPanelOuterClass,
            });
        }
    },
});
registerThreadAction("copy-invite-link", {
    condition: ({ channel, pipWindow }) => pipWindow && channel?.invitationLink,
    icon: "oi oi-fw oi-user-plus",
    name: _t("Copy Invite Link"),
    onSelected: ({ channel, pipWindow }) =>
        channel.copyInvitationLink({
            clipboard: pipWindow.navigator.clipboard,
        }),
    sequence: 20,
    sequenceGroup: ({ isDiscussContent }) => (isDiscussContent ? 10 : 20),
});
registerThreadAction("member-list", {
    actionPanelClose: ({ action, inDiscussApp, nextActiveAction, store }) => {
        if (
            action.condition &&
            inDiscussApp &&
            store.discuss?.shouldDisableMemberPanelAutoOpenFromClose(nextActiveAction)
        ) {
            store.discuss.isMemberPanelOpenByDefault = false;
        }
    },
    actionPanelComponent: ChannelMemberList,
    actionPanelComponentProps: ({ channel }) => ({ channel }),
    actionPanelOpen: ({ inDiscussApp, store }) => {
        if (inDiscussApp) {
            store.discuss.isMemberPanelOpenByDefault = true;
        }
    },
    actionPanelOuterClass: "o-discuss-ChannelMemberList bg-inherit",
    btnAttrs: { "data-available-offline": true },
    condition: ({ channel, chatWindow, isDiscussSidebarChannelActions }) =>
        channel?.hasMemberList &&
        (!chatWindow || chatWindow.isOpen) &&
        !isDiscussSidebarChannelActions,
    icon: "oi oi-fw oi-users",
    name: _t("Members"),
    sequence: 30,
    sequenceGroup: 10,
});
registerThreadAction("mark-read", {
    condition: ({ channel, isDiscussSidebarChannelActions }) =>
        channel?.self_member_id &&
        channel.self_member_id.message_unread_counter > 0 &&
        !channel.self_member_id.mute_until_dt &&
        isDiscussSidebarChannelActions,
    onSelected: ({ channel }) => channel.markAsRead(),
    icon: "fa fa-fw fa-check",
    name: _t("Mark Read"),
    sequence: 10,
    sequenceGroup: 20,
});
registerThreadAction("hide", {
    /**
     * @param {Object} param0
     * @param {import("models").DiscussChannel} param0.channel
     */
    condition: ({ channel, isDiscussContent, store }) =>
        store.self_user?.share === false &&
        (channel?.canHide || channel?.sub_channel_ids.some((subChannel) => subChannel.canHide)) &&
        !channel?.isSelfInCall &&
        !isDiscussContent,
    icon: "fa fa-fw fa-eye-slash",
    /**
     * @param {Object} param0
     * @param {import("models").DiscussChannel} param0.channel
     */
    name: ({ channel }) =>
        channel.isHideUntilNewMessageSupported ? _t("Hide Until New Message") : _t("Hide"),
    /**
     * @param {Object} param0
     * @param {import("models").DiscussChannel} param0.channel
     */
    onSelected: ({ channel }) => channel.unpinChannel(),
    sequence: 10,
    sequenceGroup: 35,
});
registerThreadAction("leave", {
    /**
     * @param {Object} param0
     * @param {import("models").DiscussChannel} param0.channel
     * @param {import("models").Store} param0.store
     */
    condition: ({ channel, isDiscussContent, store }) =>
        store.self_user &&
        channel?.self_member_id &&
        channel.allowedToLeaveChannelTypes.includes(channel.channel_type) &&
        channel.group_ids.length === 0 &&
        !isDiscussContent,
    icon: "fa fa-fw fa-sign-out",
    name: _t("Leave Channel"),
    /**
     * @param {Object} param0
     * @param {import("models").DiscussChannel} param0.channel
     */
    onSelected: ({ channel }) => channel.leaveChannel(),
    sequence: 20,
    sequenceGroup: 40,
    tags: ACTION_TAGS.DANGER,
});

registerThreadAction("delete-thread", {
    actionPanelComponent: DeleteThreadDialog,
    actionPanelComponentProps: ({ channel }) => ({ channel }),
    actionPanelOuterClass: "bg-100",
    condition({ channel, isDiscussContent, store }) {
        return (
            channel?.parent_channel_id &&
            store.self_user?.eq(channel.create_uid) &&
            !isDiscussContent
        );
    },
    icon: "fa fa-fw fa-trash",
    iconLarge: "fa fa-fw fa-lg fa-trash",
    name: _t("Delete Thread"),
    actionPanelOpen: ({ channel, isDiscussSidebarChannelActions, store }) => {
        if (isDiscussSidebarChannelActions) {
            store.env.services.dialog?.add(ChannelActionDialog, {
                title: channel.name,
                contentComponent: DeleteThreadDialog,
                contentProps: {
                    close: () => store.env.services.dialog.closeAll(),
                    channel,
                },
            });
        }
    },
    sequence: ({ chatWindow }) => (chatWindow ? 50 : 40),
    sequenceGroup: 40,
    tags: [ACTION_TAGS.DANGER],
});
