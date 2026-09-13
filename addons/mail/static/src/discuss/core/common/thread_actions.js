// @ts-check
/** @odoo-module native */
import { ACTION_TAGS } from "@mail/core/common/action";
import { registerThreadAction } from "@mail/core/common/thread_actions";
import { AttachmentPanel } from "@mail/discuss/core/common/attachment_panel";
import { ChannelInvitation } from "@mail/discuss/core/common/channel_invitation";
import { DeleteThreadDialog } from "@mail/discuss/core/common/delete_thread_dialog";
import { NotificationSettings } from "@mail/discuss/core/common/notification_settings";
import { Component, xml } from "@odoo/owl";
import { _t } from "@web/core/translation";
import { Dialog } from "@web/ui/dialog";
import { usePopover } from "@web/ui/popover";

/** @typedef {import("@mail/core/common/thread_actions").ActionParams} ActionParams */
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
    /** @param {ActionParams} params */
    condition: ({ owner, store, thread }) =>
        thread?.isChannelKind &&
        store.self_partner &&
        (!owner.props.chatWindow || owner.props.chatWindow.isOpen),
    /** @param {ActionParams} params */
    setup({ owner }) {
        if (!owner.props.chatWindow) {
            this.popover = usePopover(NotificationSettings, {
                onClose: () => this.close(),
                position: "bottom-end",
                fixedPosition: true,
                class: this.panelOuterClass,
            });
        }
    },
    /** @param {ActionParams} params */
    open({ owner, store, thread }) {
        if (owner.isDiscussSidebarChannelActions || owner.env.inMeetingView) {
            store.env.services.dialog?.add(ChannelActionDialog, {
                title: thread.displayName,
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
    /** @param {ActionParams} params */
    close: ({ action }) => action.popover?.close(),
    /** @param {ActionParams} params */
    icon: ({ thread }) =>
        thread.isMuted ? "fa-solid fa-bell-slash text-danger" : "fa-solid fa-bell",
    name: _t("Notification Settings"),
    panelOuterClass: "bg-100 border border-secondary",
    sequence: 10,
    sequenceGroup: 30,
    toggle: true,
});
registerThreadAction("attachments", {
    actionPanelComponent: AttachmentPanel,
    /** @param {ActionParams} params */
    condition: ({ owner, thread }) =>
        thread?.hasAttachmentPanel &&
        (!owner.props.chatWindow || owner.props.chatWindow.isOpen) &&
        !owner.isDiscussSidebarChannelActions,
    icon: "fa-solid fa-paperclip",
    name: _t("Attachments"),
    sequence: 10,
    sequenceGroup: 10,
    toggle: true,
});
registerThreadAction("invite-people", {
    actionPanelComponent: ChannelInvitation,
    /** @param {ActionParams} params */
    actionPanelComponentProps: ({ action }) => ({ close: () => action.close() }),
    /** @param {ActionParams} params */
    close: ({ action }) => action.popover?.close(),
    /** @param {ActionParams} params */
    condition: ({ owner, thread }) =>
        thread?.isChannelKind &&
        (!owner.props.chatWindow || owner.props.chatWindow.isOpen),
    /** @param {ActionParams} params */
    panelOuterClass: ({ owner }) =>
        `o-discuss-ChannelInvitation ${
            owner.props.chatWindow ? "bg-inherit" : ""
        } bg-100 border border-secondary`,
    icon: "oi oi-fw oi-user-plus",
    name: _t("Invite People"),
    /** @param {ActionParams} params */
    open({ owner, store, thread }) {
        if (owner.isDiscussSidebarChannelActions) {
            store.env.services.dialog?.add(ChannelActionDialog, {
                title: thread.displayName,
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
    /** @param {ActionParams} params */
    sequence: ({ owner }) => (owner.isDiscussSidebarChannelActions ? 20 : 10),
    sequenceGroup: 20,
    /** @param {ActionParams} params */
    setup({ owner }) {
        if (!owner.props.chatWindow && !owner.env.inMeetingView) {
            this.popover = usePopover(ChannelInvitation, {
                onClose: () => this.close(),
                class: this.panelOuterClass,
            });
        }
    },
    toggle: true,
});
registerThreadAction("mark-read", {
    /** @param {ActionParams} params */
    condition: ({ owner, thread }) =>
        thread?.self_member_id &&
        thread.self_member_id.message_unread_counter > 0 &&
        !thread.isMuted &&
        owner.isDiscussSidebarChannelActions,
    /** @param {ActionParams} params */
    open: ({ owner }) => owner.thread.markAsRead(),
    icon: "fa-solid fa-check",
    name: _t("Mark Read"),
    sequence: 10,
    sequenceGroup: 20,
});
registerThreadAction("delete-thread", {
    actionPanelComponent: DeleteThreadDialog,
    /** @param {ActionParams} params */
    actionPanelComponentProps({ action }) {
        return { close: () => action.close() };
    },
    /** @param {ActionParams} params */
    condition({ owner, store, thread }) {
        return (
            thread?.parent_channel_id &&
            store.selfUser?.eq(thread.create_uid) &&
            !owner.isDiscussContent
        );
    },
    panelOuterClass: "bg-100",
    icon: "fa-solid fa-trash-can",
    name: _t("Delete Thread"),
    /** @param {ActionParams} params */
    close: ({ action }) => action.popover?.close(),
    toggle: true,
    /** @param {ActionParams} params */
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
    /** @param {ActionParams} params */
    sequence: ({ owner }) => (owner.props.chatWindow ? 50 : 40),
    sequenceGroup: 40,
    tags: [ACTION_TAGS.DANGER],
});
