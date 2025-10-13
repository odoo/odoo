import { ACTION_TAGS } from "@mail/core/common/action";
import { registerThreadAction } from "@mail/core/common/thread_actions";
import { AttachmentPanel } from "@mail/discuss/core/common/attachment_panel";
import { ChannelInvitation } from "@mail/discuss/core/common/channel_invitation";
import { ChannelMemberList } from "@mail/discuss/core/common/channel_member_list";
import { DeleteThreadDialog } from "@mail/discuss/core/common/delete_thread_dialog";
import { NotificationSettings } from "@mail/discuss/core/common/notification_settings";

import { Component, xml } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";

class ChannelActionDialog extends Component {
    static props = ["title", "contentComponent", "contentProps", "close?"];
    static components = { Dialog };
    static template = xml`
        <Dialog size="'md'" title="props.title" footer="false" contentClass="'o-bg-body'" bodyClass="'p-1'">
            <t t-component="props.contentComponent" t-props="props.contentProps"/>
        </Dialog>
    `;
}

registerThreadAction("notification-settings", {
    actionPanelClose: ({ action }) => action.popover?.close(),
    actionPanelComponent: NotificationSettings,
    actionPanelOpen({ owner, store, thread }) {
        if (owner.isDiscussSidebarChannelActions || owner.env.inMeetingView) {
            store.env.services.dialog?.add(ChannelActionDialog, {
                title: thread.name,
                contentComponent: NotificationSettings,
                contentProps: { thread },
            });
        } else {
            this.popover?.open(owner.root.el.querySelector(`[name="${this.id}"]`), {
                hasSizeConstraints: true,
                thread,
            });
        }
    },
    actionPanelOuterClass: "bg-100 border border-secondary",
    condition: ({ channel, owner, store }) =>
        channel && store.self_partner && (!owner.props.chatWindow || owner.props.chatWindow.isOpen),
    setup({ owner }) {
        if (!owner.props.chatWindow) {
            this.popover = usePopover(NotificationSettings, {
                onClose: () => this.actionPanelClose(),
                position: "bottom-end",
                fixedPosition: true,
                popoverClass: this.actionPanelOuterClass,
            });
        }
    },
    icon: ({ channel }) =>
        channel.self_member_id?.mute_until_dt
            ? "fa fa-fw text-danger fa-bell-slash"
            : "fa fa-fw fa-bell",
    name: _t("Notification Settings"),
    sequence: 10,
    sequenceGroup: 30,
});
registerThreadAction("attachments", {
    actionPanelComponent: AttachmentPanel,
    condition: ({ owner, thread }) =>
        thread?.hasAttachmentPanel &&
        (!owner.props.chatWindow || owner.props.chatWindow.isOpen) &&
        !owner.isDiscussSidebarChannelActions,
    icon: "fa fa-fw fa-paperclip",
    name: _t("Attachments"),
    sequence: 10,
    sequenceGroup: 10,
});
registerThreadAction("invite-people", {
    actionPanelClose: ({ action }) => action.popover?.close(),
    actionPanelComponent: ChannelInvitation,
    actionPanelComponentProps: ({ action }) => ({ close: () => action.actionPanelClose() }),
    actionPanelOpen({ owner, store, thread }) {
        if (owner.isDiscussSidebarChannelActions) {
            store.env.services.dialog?.add(ChannelActionDialog, {
                title: thread.name,
                contentComponent: ChannelInvitation,
                contentProps: {
                    autofocus: true,
                    thread,
                    close: () => store.env.services.dialog.closeAll(),
                },
            });
        } else if (!owner.env.inMeetingView) {
            this.popover?.open(owner.root.el.querySelector(`[name="${this.id}"]`), {
                hasSizeConstraints: true,
                thread,
            });
        }
    },
    actionPanelOuterClass: ({ owner }) =>
        `o-discuss-ChannelInvitation ${
            owner.props.chatWindow ? "bg-inherit" : ""
        } bg-100 border border-secondary`,
    condition: ({ channel, owner }) =>
        channel && (!owner.props.chatWindow || owner.props.chatWindow.isOpen),
    icon: "oi oi-fw oi-user-plus",
    name: _t("Invite People"),
    sequence: ({ owner }) => (owner.isDiscussSidebarChannelActions ? 20 : 10),
    sequenceGroup: 20,
    setup({ owner }) {
        if (!owner.props.chatWindow && !owner.env.inMeetingView) {
            this.popover = usePopover(ChannelInvitation, {
                onClose: () => this.actionPanelClose(),
                popoverClass: this.actionPanelOuterClass,
            });
        }
    },
});
registerThreadAction("member-list", {
    actionPanelClose: ({ owner, store }) => {
        if (owner.env.inDiscussApp) {
            store.discuss.isMemberPanelOpenByDefault = false;
        }
    },
    actionPanelComponent: ChannelMemberList,
    actionPanelComponentProps: ({ actions }) => ({
        openChannelInvitePanel({ keepPrevious } = {}) {
            actions.actions
                .find(({ id }) => id === "invite-people")
                ?.actionPanelOpen({ keepPrevious });
        },
    }),
    actionPanelOpen: ({ owner, store }) => {
        if (owner.env.inDiscussApp) {
            store.discuss.isMemberPanelOpenByDefault = true;
        }
    },
    actionPanelOuterClass: "o-discuss-ChannelMemberList bg-inherit",
    condition: ({ owner, thread }) =>
        thread?.hasMemberList &&
        (!owner.props.chatWindow || owner.props.chatWindow.isOpen) &&
        !owner.isDiscussSidebarChannelActions,
    icon: "oi oi-fw oi-users",
    name: _t("Members"),
    sequence: 30,
    sequenceGroup: 10,
});
registerThreadAction("mark-read", {
    condition: ({ channel, owner }) =>
        channel?.self_member_id &&
        channel.self_member_id.message_unread_counter > 0 &&
        !channel.self_member_id.mute_until_dt &&
        owner.isDiscussSidebarChannelActions,
    onSelected: ({ owner }) => owner.thread.markAsRead(),
    icon: "fa fa-fw fa-check",
    name: _t("Mark Read"),
    sequence: 10,
    sequenceGroup: 20,
});
registerThreadAction("delete-thread", {
    actionPanelClose: ({ action }) => action.popover?.close(),
    actionPanelComponent: DeleteThreadDialog,
    actionPanelComponentProps({ action }) {
        return { close: () => action.actionPanelClose() };
    },
    actionPanelOuterClass: "bg-100",
    condition({ owner, store, thread }) {
        return (
            thread?.parent_channel_id &&
            store.self.main_user_id?.eq(thread.create_uid) &&
            !owner.isDiscussContent
        );
    },
    icon: "fa fa-fw fa-trash",
    iconLarge: "fa fa-fw fa-lg fa-trash",
    name: _t("Delete Thread"),
    actionPanelOpen: ({ owner, store, thread }) => {
        if (owner.isDiscussSidebarChannelActions) {
            store.env.services.dialog?.add(ChannelActionDialog, {
                title: thread.name,
                contentComponent: DeleteThreadDialog,
                contentProps: {
                    close: () => store.env.services.dialog.closeAll(),
                    thread,
                },
            });
        }
    },
    sequence: ({ owner }) => (owner.props.chatWindow ? 50 : 40),
    sequenceGroup: 40,
    tags: [ACTION_TAGS.DANGER],
});
