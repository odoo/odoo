import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { AttachmentPanel } from "@mail/discuss/core/common/attachment_panel";
import { ChannelInvitation } from "@mail/discuss/core/common/channel_invitation";
import { ChannelMemberList } from "@mail/discuss/core/common/channel_member_list";
import { NotificationSettings } from "@mail/discuss/core/common/notification_settings";

import { useComponent } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";

threadActionsRegistry
    .add("notification-settings", {
        condition(component) {
            return (
                component.thread?.model === "discuss.channel" &&
                component.store.self.type !== "guest" &&
                (!component.props.chatWindow || component.props.chatWindow.isOpen)
            );
        },
        setup(action) {
            const component = useComponent();
            if (!component.props.chatWindow) {
                action.popover = usePopover(NotificationSettings, {
                    onClose: () => action.close(),
                    position: "bottom-end",
                    fixedPosition: true,
                    popoverClass: action.panelOuterClass,
                });
            }
        },
        open(component, action) {
            action.popover?.open(component.root.el.querySelector(`[name="${action.id}"]`), {
                hasSizeConstraints: true,
                thread: component.thread,
            });
        },
        close(component, action) {
            action.popover?.close();
        },
        component: NotificationSettings,
        icon(component) {
            return component.thread.isMuted
                ? "fa fa-fw text-danger fa-bell-slash"
                : "fa fa-fw fa-bell";
        },
        iconLarge(component) {
            return component.thread.isMuted
                ? "fa fa-fw fa-lg text-danger fa-bell-slash"
                : "fa fa-fw fa-lg fa-bell";
        },
        name: _t("Notification Settings"),
        sequence: 10,
        sequenceGroup: 30,
        toggle: true,
    })
    .add("attachments", {
        condition: (component) =>
            component.thread?.hasAttachmentPanel &&
            (!component.props.chatWindow || component.props.chatWindow.isOpen),
        component: AttachmentPanel,
        icon: "fa fa-fw fa-paperclip",
        iconLarge: "fa fa-fw fa-lg fa-paperclip",
        name: _t("Attachments"),
        sequence: 10,
        sequenceGroup: 10,
        toggle: true,
    })
    .add("invite-people", {
        close(component, action) {
            action.popover?.close();
        },
        component: ChannelInvitation,
        componentProps(action) {
            return { close: () => action.close() };
        },
        condition(component) {
            return (
                component.thread?.model === "discuss.channel" &&
                (!component.props.chatWindow || component.props.chatWindow.isOpen)
            );
        },
        panelOuterClass(component) {
            return `o-discuss-ChannelInvitation ${component.props.chatWindow ? "bg-inherit" : ""}`;
        },
        icon: "fa fa-fw fa-user-plus",
        iconLarge: "fa fa-fw fa-lg fa-user-plus",
        name: _t("Invite People"),
        open(component, action) {
            action.popover?.open(component.root.el.querySelector(`[name="${action.id}"]`), {
                hasSizeConstraints: true,
                thread: component.thread,
            });
        },
        sequence: 10,
        sequenceGroup: 20,
        setup(action) {
            const component = useComponent();
            if (!component.props.chatWindow) {
                action.popover = usePopover(ChannelInvitation, {
                    onClose: () => action.close(),
                    popoverClass: action.panelOuterClass,
                });
            }
        },
        toggle: true,
    })
    .add("member-list", {
        component: ChannelMemberList,
        condition(component) {
            return (
                component.thread?.hasMemberList &&
                (!component.props.chatWindow || component.props.chatWindow.isOpen)
            );
        },
        componentProps(action, component) {
            return {
                openChannelInvitePanel({ keepPrevious } = {}) {
                    component.threadActions.actions
                        .find(({ id }) => id === "invite-people")
                        ?.open({ keepPrevious });
                },
            };
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
    });
