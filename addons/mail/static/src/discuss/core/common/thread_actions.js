import { useSubEnv } from "@web/owl2/utils";
import { ACTION_GROUP_TAGS, ACTION_TAGS } from "@mail/core/common/action";
import { describeThreadActionGroup, registerThreadAction } from "@mail/core/common/thread_actions";
import { AttachmentPanel } from "@mail/discuss/core/common/attachment_panel";
import { ChannelInvitation } from "@mail/discuss/core/common/channel_invitation";
import { ChannelMemberList } from "@mail/discuss/core/common/channel_member_list";
import { DeleteThreadDialog } from "@mail/discuss/core/common/delete_thread_dialog";
import { NotificationSettings } from "@mail/discuss/core/common/notification_settings";
import { PinnedMessagesPanel } from "@mail/discuss/core/common/pinned_messages_panel";
import { attClassObjectToString } from "@mail/utils/common/format";

import { _t } from "@web/core/l10n/translation";

describeThreadActionGroup(10, { tags: ACTION_GROUP_TAGS.INLINE_SWITCHER_LOOK });

registerThreadAction("pinned-messages", {
    btnAttrs: { "data-available-offline": true },
    condition: ({ channel, owner }) =>
        channel &&
        (!owner.props.chatWindow || owner.props.chatWindow.isOpen) &&
        !owner.isDiscussSidebarChannelActions,
    icon: "push_pin",
    name: ({ action }) => (action.isActive ? _t("Hide Pinned Messages") : _t("Pinned Messages")),
    panel: {
        class: "o-discuss-PinnedMessagesPanel bg-inherit",
        component: PinnedMessagesPanel,
        props: ({ channel }) => ({ channel }),
    },
    sequence: 20,
    sequenceGroup: 10,
    setup() {
        useSubEnv({
            pinMenu: {
                open: () => this.openPanel({ keepPrevious: true }),
                close: () => {
                    if (this.isActive) {
                        this.closePanel();
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
    condition: ({ channel, store, owner }) =>
        store.self_user?.share === false &&
        channel &&
        channel.self_member_id &&
        !channel.self_member_id.is_favorite &&
        !owner.isDiscussContent,
    icon: "star",
    name: _t("Add to Favorites"),
    /**
     * @param {Object} param0
     * @param {import("models").DiscussChannel} param0.channel
     * @param {import("models").Store} param0.store
     */
    onSelected: async ({ channel, store, owner }) => {
        store.fetchStoreData(
            "/discuss/channel/favorite",
            { channel_id: channel.id, is_favorite: true },
            { silent: false }
        );
        if (owner.env.inDiscussApp && !owner.env.services.ui.isSmall) {
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
    condition: ({ channel, owner }) =>
        channel?.self_member_id?.is_favorite && !owner.isDiscussContent,
    icon: "star",
    name: _t("Remove from Favorites"),
    /**
     * @param {Object} param0
     * @param {import("models").DiscussChannel} param0.channel
     * @param {import("models").Store} param0.store
     */
    onSelected: async ({ channel, store, owner }) => {
        store.fetchStoreData(
            "/discuss/channel/favorite",
            { channel_id: channel.id, is_favorite: false },
            { silent: false }
        );
        if (owner.env.inDiscussApp && !owner.env.services.ui.isSmall) {
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
    condition: ({ channel, owner, store }) =>
        channel && store.self_user && (!owner.props.chatWindow || owner.props.chatWindow.isOpen),
    icon: ({ channel }) =>
        channel?.self_member_id?.mute_until_dt ? "notifications_off" : "notifications",
    iconClass: ({ channel }) =>
        `oi-filled oi-fw ${channel?.self_member_id?.mute_until_dt ? "text-danger" : ""}`,
    name: ({ channel }) =>
        channel.channel_type == "channel" ? _t("Notification Settings") : _t("Mute Conversation"),
    panel: {
        class: ({ owner, store }) => store.discussDropdownMenuClass(owner),
        component: NotificationSettings,
        props: ({ channel }) => ({ channel }),
    },
    sequence: 10,
    sequenceGroup: 30,
});
registerThreadAction("attachments", {
    btnAttrs: { "data-available-offline": true },
    condition: ({ owner, channel }) =>
        channel?.hasAttachmentPanel &&
        (!owner.props.chatWindow || owner.props.chatWindow.isOpen) &&
        !owner.isDiscussSidebarChannelActions,
    icon: "attach_file",
    name: _t("Attachments"),
    panel: { component: AttachmentPanel, props: ({ channel }) => ({ channel }) },
    sequence: 10,
    sequenceGroup: 10,
});
registerThreadAction("invite-people", {
    condition: ({ channel, owner }) =>
        channel &&
        !owner.env.pipWindow &&
        (!owner.props.chatWindow || owner.props.chatWindow.isOpen) &&
        !(owner.isDiscussContent && channel?.hasMemberList),
    icon: "person_add",
    name: _t("Invite People"),
    panel: {
        class: ({ owner, store }) =>
            attClassObjectToString({
                "o-discuss-ChannelInvitation border": true,
                "bg-inherit": owner.props.chatWindow,
                [store.discussDropdownMenuClass(owner)]: !owner.env.inMeetingView,
            }),
        component: ChannelInvitation,
        props: ({ channel }) => ({ channel }),
    },
    sequence: 20,
    sequenceGroup: ({ owner }) => (owner.isDiscussContent ? 10 : 20),
});
registerThreadAction("copy-invite-link", {
    condition: ({ channel, owner }) => owner.env.pipWindow && channel?.invitationLink,
    icon: "person_add",
    name: _t("Copy Invite Link"),
    onSelected: ({ channel, owner }) =>
        channel.copyInvitationLink({
            clipboard: owner.env.pipWindow.navigator.clipboard,
        }),
    sequence: 20,
    sequenceGroup: ({ owner }) => (owner.isDiscussContent ? 10 : 20),
});
registerThreadAction("member-list", {
    btnAttrs: { "data-available-offline": true },
    condition: ({ owner, channel }) =>
        channel?.hasMemberList &&
        (!owner.props.chatWindow || owner.props.chatWindow.isOpen) &&
        !owner.isDiscussSidebarChannelActions,
    icon: "group",
    name: _t("Members"),
    panel: {
        class: "o-discuss-ChannelMemberList bg-inherit",
        component: ChannelMemberList,
        onClose: ({ action, owner, store, nextActiveAction }) => {
            if (
                action.condition &&
                owner.env.inDiscussApp &&
                store.discuss?.shouldDisableMemberPanelAutoOpenFromClose(nextActiveAction)
            ) {
                store.discuss.isMemberPanelOpenByDefault = false;
            }
        },
        onOpen: ({ owner, store }) => {
            if (owner.env.inDiscussApp) {
                store.discuss.isMemberPanelOpenByDefault = true;
            }
        },
        props: ({ channel }) => ({ channel }),
    },
    sequence: 30,
    sequenceGroup: 10,
});
registerThreadAction("meeting-to-chat", {
    condition: ({ channel, owner }) =>
        channel?.default_display_mode === "video_full_screen" &&
        !owner.isDiscussContent &&
        ["owner", "admin"].includes(channel.self_member_id?.channel_role),
    icon: "group",
    name: _t("Convert to Chat"),
    onSelected: ({ channel, store }) => {
        store.fetchStoreData(
            "/discuss/channel/meeting_to_group_chat",
            { channel_id: channel.id },
            { silent: false }
        );
    },
    sequence: 15,
    sequenceGroup: 30,
});
registerThreadAction("mark-read", {
    condition: ({ channel, owner }) =>
        channel?.self_member_id &&
        channel.self_member_id.message_unread_counter > 0 &&
        !channel.self_member_id.mute_until_dt &&
        owner.isDiscussSidebarChannelActions,
    onSelected: ({ channel }) => channel.markAsRead(),
    icon: "check",
    name: _t("Mark Read"),
    sequence: 10,
    sequenceGroup: 20,
});
registerThreadAction("hide", {
    /**
     * @param {Object} param0
     * @param {import("models").DiscussChannel} param0.channel
     */
    condition: ({ channel, store, owner }) =>
        store.self_user?.share === false &&
        (channel?.canHide || channel?.sub_channel_ids.some((subChannel) => subChannel.canHide)) &&
        !channel?.isSelfInCall &&
        !owner.isDiscussContent,
    icon: "visibility_off",
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
    condition: ({ channel, owner }) => channel?.isAllowedToLeave && !owner.isDiscussContent,
    icon: "logout",
    name: _t("Leave Conversation"),
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
    condition({ channel, owner, store }) {
        return (
            channel?.parent_channel_id &&
            store.self_user?.eq(channel.create_uid) &&
            !owner.isDiscussContent
        );
    },
    icon: "delete",
    iconLarge: "delete",
    name: _t("Delete Thread"),
    panel: {
        class: "bg-100",
        component: DeleteThreadDialog,
        props: ({ channel }) => ({ channel }),
    },
    sequence: ({ owner }) => (owner.props.chatWindow ? 50 : 40),
    sequenceGroup: 40,
    tags: [ACTION_TAGS.DANGER],
});
