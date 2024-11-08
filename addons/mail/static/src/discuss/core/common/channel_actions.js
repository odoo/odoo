import { useComponent, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { NotificationSettings } from "@mail/discuss/core/common/notification_settings";
import { ChannelInvitation } from "@mail/discuss/core/common/channel_invitation";

export const channelActionsRegistry = registry.category("discuss.sidebar/actions");

channelActionsRegistry
    .add("mark-as-read", {
        condition: (component) => {
            return (
                component.props.thread?.selfMember?.message_unread_counter > 0 &&
                !component.props.thread.mute_until_dt
            );
        },
        executeAction: (component) => {
            component.props.thread.markAsRead();
        },
        icon: "fa fa-fw fa-check",
        name: _t("Mark as read"),
        sequence: 1,
        text: "markasread",
    })
    .add("channel-details", {
        condition: (component) => {
            return component.props.thread;
        },
        executeAction: (component) => {
            component.channelInfo(component.props.thread);
        },
        icon: "fa fa-fw fa-cog",
        name: _t("Channel Info"),
        sequence: 2,
        text: "channeldetails",
    })
    .add("leave-channel", {
        condition: (component) => {
            return component.props.thread.canLeave;
        },
        executeAction: (component) => {
            component.leaveChannel(component.props.thread);
        },
        icon: "fa fa-fw fa-sign-out",
        name: _t("Leave Channel"),
        sequence: 3,
        text: "leavechannel",
    })
    .add("unpin-channel", {
        condition: (component) => {
            return component.props.thread.canUnpin;
        },
        executeAction: (component) => {
            component.props.thread.unpin();
        },
        icon: "fa fa-fw fa-times",
        name: _t("Unpin Conversation"),
        sequence: 4,
        text: "unpinchannel",
    })
    .add("add-users", {
        condition(component) {
            return component.props.thread?.model === "discuss.channel";
        },
        component: ChannelInvitation,
        icon: "fa fa-fw fa-user-plus",
        name: _t("Invite People"),
        isInteractiveAction: true,
        sequence: 6,
        text: "adduser",
    })
    .add("notification-settings", {
        condition: (component) => {
            return (
                component.props.thread?.model === "discuss.channel" &&
                !component.store.discuss.chatWindow &&
                component.store.self.type !== "guest"
            );
        },
        component: NotificationSettings,
        icon(component) {
            return component.props.thread.mute_until_dt
                ? "fa fa-fw fa-bell-slash"
                : "fa fa-fw fa-bell";
        },
        name: _t("Notification Settings"),
        isInteractiveAction: true,
        sequence: 5,
        text: "notification",
    });

function transformAction(component, id, action) {
    return {
        /** Optional component that should be displayed in the view when this action is active. */
        component: action.component,
        /** Condition to display this action. */
        get condition() {
            return action.condition(component);
        },
        /** Execition that is carried out  */
        get executeAction() {
            return action.executeAction(component);
        },
        /** Icon for the button this action. */
        get icon() {
            return typeof action.icon === "function" ? action.icon(component) : action.icon;
        },
        /** Unique id of this action. */
        id,
        /** Name of this action, displayed to the user. */
        get name() {
            return action.name;
        },
        /** Determines whether the action is expandable or. */
        isInteractiveAction: action.isInteractiveAction,
        /** Determines the order of this action (smaller first). */
        get sequence() {
            return typeof action.sequence === "function"
                ? action.sequence(component)
                : action.sequence;
        },
        /** Determines the text of the action. */
        text: action.text,
    };
}

export function useChannelActions() {
    const component = useComponent();
    const transformedActions = channelActionsRegistry
        .getEntries()
        .map(([id, action]) => transformAction(component, id, action));
    const state = useState({
        get actions() {
            return transformedActions
                .filter((action) => action.condition)
                .sort((a1, a2) => a1.sequence - a2.sequence);
        },
        activeAction: null,
    });
    return state;
}
