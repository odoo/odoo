import { useComponent, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { NotificationSettings } from "@mail/discuss/core/common/notification_settings";
import { ChannelInvitation } from "./channel_invitation";

export const sidebarActionsRegistry = registry.category("discuss.sidebar/actions");

sidebarActionsRegistry
    .add("mark-as-read", {
        condition: (component) => {
            return (
                component.props.thread?.selfMember?.message_unread_counter > 0 &&
                !component.props.thread.mute_until_dt
            );
        },
        executeAction(component) {
            component.props.thread.markAsRead({ sync: true });
        },
        icon: "fa fa-fw fa-check",
        iconLarge: "fa fa-fw fa-lg fa-check",
        name: _t("Mark as read"),
        nameActive: _t("Mark as read"),
        sequence: 1,
    })
    .add("add-users", {
        condition(component) {
            return component.props.thread?.model === "discuss.channel";
        },
        close(component, action) {
            action.popover?.close();
        },
        component: ChannelInvitation,
        setup(action) {
            this.popover = usePopover(ChannelInvitation, {
                onClose: () => this.close(),
                popoverClass: action.panelOuterClass,
                position: "right-start",
            });
        },
        icon: "fa fa-fw fa-user-plus",
        iconLarge: "fa fa-fw fa-lg fa-user-plus",
        name: _t("Invite People"),
        nameActive: _t("Stop Inviting"),
        open(component, action) {
            action.popover?.open(
                component.root.el.querySelector(`[title="${action.name.toString()}"]`),
                {
                    hasSizeConstraints: true,
                    thread: component.props.thread,
                }
            );
        },
        panelOuterClass: "o-discuss-ChannelInvitation",
        popover: true,
        sequence: 2,
        subMenu: true,
        toggle: true,
    })
    .add("notification-settings", {
        condition: (component) => {
            return (
                component.props.thread?.model === "discuss.channel" &&
                !component.store.discuss.chatWindow &&
                component.store.self.type !== "guest"
            );
        },
        close(component, action) {
            action.popover?.close();
        },
        component: NotificationSettings,
        setup(action) {
            this.popover = usePopover(NotificationSettings, {
                onClose: () => {
                    this.close();
                },
                position: "right-start",
                fixedPosition: true,
                popoverClass: action.panelOuterClass,
            });
        },
        icon(component) {
            return component.props.thread.mute_until_dt
                ? "fa fa-fw fa-bell-slash"
                : "fa fa-fw fa-bell";
        },
        iconLarge(component) {
            return component.props.thread.mute_until_dt
                ? "fa fa-fw fa-lg fa-bell-slash"
                : "fa fa-fw fa-lg fa-bell";
        },
        name: _t("Notification Settings"),
        open(component, action) {
            action.popover?.open(
                component.root.el.querySelector(`[title="${action.name.toString()}"]`),
                {
                    hasSizeConstraints: true,
                    thread: component.props.thread,
                }
            );
        },
        popover: true,
        subMenu: true,
        sequence: 3,
        toggle: true,
    })
    .add("channel-details", {
        condition: (component) => {
            return component.props.thread;
        },
        executeAction(component) {
            component.channelInfo(component.props.thread);
        },
        icon: "fa fa-fw fa-cog",
        iconLarge: "fa fa-fw fa-lg fa-cog",
        name: _t("Channel Info"),
        nameActive: _t("Channel Info"),
        sequence: 4,
        toggle: true,
    })
    .add("leave-channel", {
        condition: (component) => {
            return component.props.thread.canLeave;
        },
        executeAction(component) {
            component.leaveChannel(component.props.thread);
            component.props.close();
        },
        icon: "fa fa-fw fa-sign-out",
        iconLarge: "fa fa-fw fa-sign-out",
        name: _t("Leave this channel"),
        nameActive: _t("Leave this channel"),
        sequence: 5,
        toggle: true,
    })
    .add("unpin-channel", {
        condition: (component) => {
            return component.props.thread.canUnpin;
        },
        executeAction(component) {
            component.props.thread.unpin();
            component.props.close();
        },
        icon: "fa fa-fw fa-times",
        iconLarge: "fa fa-fw fa-times",
        name: _t("Unpin Conversation"),
        nameActive: _t("Unpin Conversation"),
        sequence: 6,
        toggle: true,
    });

function transformAction(component, id, action) {
    return {
        /** Closes this action. */
        close() {
            if (this.toggle) {
                component.sidebarChannelActions.activeAction =
                    component.sidebarChannelActions.actionStack.pop();
            }
            action.close?.(component, this);
        },
        /** Optional component that should be displayed in the view when this action is active. */
        component: action.component,
        /** Condition to display this action. */
        get condition() {
            return action.condition(component);
        },
        /** Condition to disable the sub-menu icon */
        get subMenu() {
            return action.subMenu;
        },
        /** Icon for the button this action. */
        get icon() {
            return typeof action.icon === "function" ? action.icon(component) : action.icon;
        },
        /** Large icon for the button this action. */
        get iconLarge() {
            return typeof action.iconLarge === "function"
                ? action.iconLarge(component)
                : action.iconLarge ?? action.icon;
        },
        /** Unique id of this action. */
        id,
        /** Name of this action, displayed to the user. */
        get name() {
            const res = this.isActive && action.nameActive ? action.nameActive : action.name;
            return typeof res === "function" ? res(component) : res;
        },
        /** Action to execute when this action is selected. */
        onSelect() {
            if (action.popover) {
                this.open();
            } else {
                action.executeAction(component);
                component.props.close();
            }
        },
        /** Opens this action. */
        open() {
            if (this.toggle) {
                if (component.sidebarChannelActions.activeAction) {
                    component.sidebarChannelActions.actionStack.push(
                        component.sidebarChannelActions.activeAction
                    );
                }
                component.sidebarChannelActions.activeAction = this;
            }
            action.open?.(component, this);
        },
        panelOuterClass: action.panelOuterClass,
        /** Determines whether this is a popover linked to this action. */
        popover: null,
        /** Determines the order of this action (smaller first). */
        get sequence() {
            return typeof action.sequence === "function"
                ? action.sequence(component)
                : action.sequence;
        },
        /** Component setup to execute when this action is registered. */
        setup: action.setup,
        /** Text for the button of this action */
        text: action.text,
        /** Determines whether this action is a one time effect or can be toggled (on or off). */
        toggle: action.toggle,
    };
}

export function useSidebarActions() {
    const component = useComponent();
    const transformedActions = sidebarActionsRegistry
        .getEntries()
        .map(([id, action]) => transformAction(component, id, action));
    for (const action of transformedActions) {
        if (action.setup) {
            action.setup(component);
        }
    }
    const state = useState({
        get actions() {
            return transformedActions
                .filter((action) => action.condition)
                .sort((a1, a2) => a1.sequence - a2.sequence);
        },
        actionStack: [],
        activeAction: null,
    });
    return state;
}
