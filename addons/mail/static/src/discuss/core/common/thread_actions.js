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
    actionPanelComponent: NotificationSettings,
    condition: ({ owner, store, thread }) =>
        thread?.model === "discuss.channel" &&
        store.self_partner &&
        (!owner.props.chatWindow || owner.props.chatWindow.isOpen),
    setup({ owner }) {
        if (!owner.props.chatWindow) {
            this.popover = usePopover(NotificationSettings, {
                onClose: () => this.close(),
                position: "bottom-end",
                fixedPosition: true,
                popoverClass: this.panelOuterClass,
            });
        }
    },
    open({ owner, store, thread }) {
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
    close: ({ action }) => action.popover?.close(),
    icon: ({ thread }) =>
        thread.self_member_id?.mute_until_dt
            ? "fa fa-fw text-danger fa-bell-slash"
            : "fa fa-fw fa-bell",
    name: _t("Notification Settings"),
    panelOuterClass: "bg-100 border border-secondary",
    sequence: 10,
    sequenceGroup: 30,
    toggle: true,
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
    toggle: true,
});
registerThreadAction("invite-people", {
    actionPanelComponent: ChannelInvitation,
    actionPanelComponentProps: ({ action }) => ({ close: () => action.close() }),
    close: ({ action }) => action.popover?.close(),
    condition: ({ owner, thread }) =>
        thread?.model === "discuss.channel" &&
        (!owner.props.chatWindow || owner.props.chatWindow.isOpen),
    panelOuterClass: ({ owner }) =>
        `o-discuss-ChannelInvitation ${
            owner.props.chatWindow ? "bg-inherit" : ""
        } bg-100 border border-secondary`,
    icon: "oi oi-fw oi-user-plus",
    name: _t("Invite People"),
    open({ owner, store, thread }) {
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
    sequence: ({ owner }) => (owner.isDiscussSidebarChannelActions ? 20 : 10),
    sequenceGroup: 20,
    setup({ owner }) {
        if (!owner.props.chatWindow && !owner.env.inMeetingView) {
            this.popover = usePopover(ChannelInvitation, {
                onClose: () => this.close(),
                popoverClass: this.panelOuterClass,
            });
        }
    },
    toggle: true,
});
registerThreadAction("member-list", {
    actionPanelComponent: ChannelMemberList,
    actionPanelComponentProps: ({ owner }) => ({
        openChannelInvitePanel({ keepPrevious } = {}) {
            owner.threadActions.actions
                .find(({ id }) => id === "invite-people")
                ?.open({ keepPrevious });
        },
    }),
    condition: ({ owner, thread }) =>
        thread?.hasMemberList &&
        (!owner.props.chatWindow || owner.props.chatWindow.isOpen) &&
        !owner.isDiscussSidebarChannelActions,
    panelOuterClass: "o-discuss-ChannelMemberList bg-inherit",
    icon: "oi oi-fw oi-users",
    name: _t("Members"),
    close: ({ owner, store }) => {
        if (owner.env.inDiscussApp) {
            store.discuss.isMemberPanelOpenByDefault = false;
        }
    },
    open: ({ owner, store }) => {
        if (owner.env.inDiscussApp) {
            store.discuss.isMemberPanelOpenByDefault = true;
        }
    },
    sequence: 30,
    sequenceGroup: 10,
    toggle: true,
});
registerThreadAction("mark-read", {
    condition: ({ owner, thread }) =>
        thread?.self_member_id &&
        thread.self_member_id.message_unread_counter > 0 &&
        !thread.self_member_id.mute_until_dt &&
        owner.isDiscussSidebarChannelActions,
    open: ({ owner }) => owner.thread.markAsRead(),
    icon: "fa fa-fw fa-check",
    name: _t("Mark Read"),
    sequence: 10,
    sequenceGroup: 20,
});
registerThreadAction("delete-thread", {
    actionPanelComponent: DeleteThreadDialog,
    actionPanelComponentProps({ action }) {
        return { close: () => action.close() };
    },
    condition({ owner, store, thread }) {
        return (
            thread?.parent_channel_id &&
            store.self.main_user_id?.eq(thread.create_uid) &&
            !owner.isDiscussContent
        );
    },
    panelOuterClass: "bg-100",
    icon: "fa fa-fw fa-trash",
    iconLarge: "fa fa-fw fa-lg fa-trash",
    name: _t("Delete Thread"),
    close: ({ action }) => action.popover?.close(),
    toggle: true,
    open: ({ action, owner, store, thread }) => {
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
