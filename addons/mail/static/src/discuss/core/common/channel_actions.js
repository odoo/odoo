import { ChannelInvitation } from "@mail/discuss/core/common/channel_invitation";
import { NotificationSettings } from "@mail/discuss/core/common/notification_settings";

import { useComponent, useState, Component, xml } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";

export const channelActionsRegistry = registry.category("discuss.sidebar/actions");

/**
 * A reusable dialog wrapper component that encapsulates common dialog functionality.
 *
 * @typedef {Object} Props
 * @property {string} title - Dialog header title text
 * @property {string} [size='md'] - Dialog size variants ('sm'|'md'|'lg'|'xl')
 * @property {boolean} [footer=false] - Controls footer visibility
 * @property {import("@odoo/owl").Component} contentComponent - Component to be rendered in dialog body
 * @property {Object} [contentProps] - Properties passed to the ContentComponent
 * @extends {Component<Props, Env>}
 */
export class ChannelActionDialog extends Component {
    static props = {
        title: String,
        size: { type: String, optional: true },
        footer: { type: Boolean, optional: true },
        contentComponent: Function,
        contentProps: { type: Object, optional: true },
    };
    static components = { Dialog };
    static template = xml`
        <Dialog size="props.size || 'md'" footer="props.footer ?? false" title="props.title">
            <t t-component="props.contentComponent" t-props="props.contentProps"/>
        </Dialog>
    `;
}

channelActionsRegistry
    .add("mark-as-read", {
        condition: (component) =>
            component.props.thread?.selfMember?.message_unread_counter > 0 &&
            !component.props.thread.mute_until_dt,
        executeAction: (component) => {
            component.props.thread.markAsRead();
        },
        icon: "fa fa-fw fa-check",
        name: _t("Mark as read"),
        sequence: 10,
        text: "markasread",
    })
    .add("channel-details", {
        condition: (component) => component.props.thread,
        executeAction: (component) => {
            component.channelInfo(component.props.thread);
        },
        icon: "fa fa-fw fa-info",
        name: _t("Channel Info"),
        sequence: 20,
        text: "channeldetails",
    })
    .add("leave-channel", {
        condition: (component) => component.props.thread.canLeave,
        executeAction: (component) => {
            component.leaveChannel(component.props.thread);
        },
        icon: "fa fa-fw fa-sign-out",
        name: _t("Leave Channel"),
        sequence: 30,
        text: "leavechannel",
    })
    .add("unpin-channel", {
        condition: (component) => component.props.thread.canUnpin,
        executeAction: (component) => {
            component.props.thread.unpin();
        },
        icon: "fa fa-fw fa-times",
        name: _t("Unpin Conversation"),
        sequence: 40,
        text: "unpinchannel",
    })
    .add("notification-settings", {
        condition: (component) =>
            component.props.thread.channel_type === "channel" &&
            component.props.thread?.model === "discuss.channel" &&
            !component.store.discuss.chatWindow &&
            component.store.self.type !== "guest",
        executeAction: (component) => {
            component.dialogService.add(ChannelActionDialog, {
                title: _t("Notification Settings"),
                contentComponent: NotificationSettings,
                contentProps: {
                    thread: component.props.thread,
                    showMuteOptions: false,
                },
            });
        },
        icon(component) {
            return component.props.thread.mute_until_dt
                ? "fa fa-fw fa-bell-slash"
                : "fa fa-fw fa-bell";
        },
        name: _t("Notification Settings"),
        sequence: 50,
        text: "notification",
    })
    .add("add-users", {
        condition(component) {
            return component.props.thread?.model === "discuss.channel";
        },
        executeAction: (component) => {
            component.dialogService.add(ChannelActionDialog, {
                title: _t("Channel Invitation"),
                contentComponent: ChannelInvitation,
                contentProps: {
                    autofocus: true,
                    thread: component.props.thread,
                },
            });
        },
        icon: "fa fa-fw fa-user-plus",
        name: _t("Invite People"),
        sequence: 60,
        text: "adduser",
    });

function transformAction(component, id, action) {
    return {
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
    });
    return state;
}
