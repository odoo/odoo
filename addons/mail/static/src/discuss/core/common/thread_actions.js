import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { AttachmentPanel } from "@mail/discuss/core/common/attachment_panel";
import { ChannelInvitation } from "@mail/discuss/core/common/channel_invitation";
import { ChannelMemberList } from "@mail/discuss/core/common/channel_member_list";
import { NotificationSettings } from "@mail/discuss/core/common/notification_settings";

import { Component, xml } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";

class ChannelActionDialog extends Component {
    static props = ["title", "contentComponent", "contentProps", "close?"];
    static components = { Dialog };
    static template = xml`
        <Dialog size="'md'" title="props.title" footer="false" contentClass="'o-bg-body'" bodyClass="'p-1'">
            <t t-component="props.contentComponent" t-props="props.contentProps"/>
        </Dialog>
    `;
}

threadActionsRegistry
    .add("notification-settings", {
        actionPanelComponent: NotificationSettings,
        condition(component) {
            return (
                component.thread?.model === "discuss.channel" &&
                component.store.self_partner &&
                (!component.props.chatWindow || component.props.chatWindow.isOpen)
            );
        },
        setup(component) {
            if (!component.props.chatWindow) {
                this.popover = usePopover(NotificationSettings, {
                    onClose: () => this.close(),
                    position: "bottom-end",
                    fixedPosition: true,
                    popoverClass: this.panelOuterClass,
                });
            }
            this.dialogService = useService("dialog");
            component.store = useService("mail.store");
        },
        open(component, action) {
            if (action.sidebar) {
                action.dialogService?.add(ChannelActionDialog, {
                    title: component.thread.name,
                    contentComponent: NotificationSettings,
                    contentProps: {
                        thread: component.thread,
                    },
                });
            } else {
                action.popover?.open(component.root.el.querySelector(`[name="${action.id}"]`), {
                    hasSizeConstraints: true,
                    thread: component.thread,
                });
            }
        },
        close(component, action) {
            action.popover?.close();
        },
        icon(component) {
            return component.thread.selfMember?.mute_until_dt
                ? "fa fa-fw text-danger fa-bell-slash"
                : "fa fa-fw fa-bell";
        },
        iconLarge(component) {
            return component.thread.selfMember?.mute_until_dt
                ? "fa fa-fw fa-lg text-danger fa-bell-slash"
                : "fa fa-fw fa-lg fa-bell";
        },
        name: _t("Notification Settings"),
        panelOuterClass: "bg-100 border border-secondary",
        sequence: 10,
        sequenceGroup: 30,
        sidebarSequence: 10,
        sidebarSequenceGroup: 30,
        toggle: true,
    })
    .add("attachments", {
        actionPanelComponent: AttachmentPanel,
        condition: (component) =>
            component.thread?.hasAttachmentPanel &&
            (!component.props.chatWindow || component.props.chatWindow.isOpen),
        icon: "fa fa-fw fa-paperclip",
        iconLarge: "fa fa-fw fa-lg fa-paperclip",
        name: _t("Attachments"),
        sequence: 10,
        sequenceGroup: 10,
        toggle: true,
    })
    .add("invite-people", {
        actionPanelComponent: ChannelInvitation,
        actionPanelComponentProps(component, action) {
            return { close: () => action.close() };
        },
        close(component, action) {
            action.popover?.close();
        },
        condition(component) {
            return (
                component.thread?.model === "discuss.channel" &&
                (!component.props.chatWindow || component.props.chatWindow.isOpen)
            );
        },
        panelOuterClass(component) {
            return `o-discuss-ChannelInvitation ${
                component.props.chatWindow ? "bg-inherit" : ""
            } bg-100 border border-secondary`;
        },
        icon: "fa fa-fw fa-user-plus",
        iconLarge: "fa fa-fw fa-lg fa-user-plus",
        name: _t("Invite People"),
        open(component, action) {
            if (action.sidebar) {
                action.dialogService?.add(ChannelActionDialog, {
                    title: component.thread.name,
                    contentComponent: ChannelInvitation,
                    contentProps: {
                        autofocus: true,
                        thread: component.thread,
                        close: () => {
                            action.dialogService.closeAll();
                        },
                    },
                });
            } else {
                action.popover?.open(component.root.el.querySelector(`[name="${action.id}"]`), {
                    hasSizeConstraints: true,
                    thread: component.thread,
                });
            }
        },
        sequence: 10,
        sequenceGroup: 20,
        setup(component) {
            if (!component.props.chatWindow) {
                this.popover = usePopover(ChannelInvitation, {
                    onClose: () => this.close(),
                    popoverClass: this.panelOuterClass,
                });
            }
            this.dialogService = useService("dialog");
        },
        sidebarSequence: 20,
        sidebarSequenceGroup: 20,
        toggle: true,
    })
    .add("member-list", {
        actionPanelComponent: ChannelMemberList,
        actionPanelComponentProps(component, action) {
            return {
                openChannelInvitePanel({ keepPrevious } = {}) {
                    component.threadActions.actions
                        .find(({ id }) => id === "invite-people")
                        ?.open({ keepPrevious });
                },
            };
        },
        condition(component) {
            return (
                component.thread?.hasMemberList &&
                (!component.props.chatWindow || component.props.chatWindow.isOpen)
            );
        },
        panelOuterClass: "o-discuss-ChannelMemberList bg-inherit",
        icon: "fa fa-fw fa-users",
        iconLarge: "fa fa-fw fa-lg fa-users",
        name: _t("Members"),
        close(component) {
            if (component.env.inDiscussApp) {
                component.store.discuss.isMemberPanelOpenByDefault = false;
            }
        },
        open(component) {
            if (component.env.inDiscussApp) {
                component.store.discuss.isMemberPanelOpenByDefault = true;
            }
        },
        sequence: 30,
        sequenceGroup: 10,
        toggle: true,
    })
    .add("mark-read", {
        condition: (component) =>
            component.thread?.selfMember &&
            component.thread.selfMember.message_unread_counter > 0 &&
            !component.thread.selfMember.mute_until_dt,
        open: (component) => component.thread.markAsRead(),
        icon: "fa fa-fw fa-check",
        iconLarge: "fa fa-lg fa-fw fa-check",
        name: _t("Mark Read"),
        partition: false,
        sidebarSequence: 10,
        sidebarSequenceGroup: 20,
    });
