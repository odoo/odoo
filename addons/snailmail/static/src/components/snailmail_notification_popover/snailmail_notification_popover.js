/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export default class SnailmailNotificationPopoverContentView extends Component {

    /**
     * @returns {string}
     */
    get iconClass() {
        switch (this.notification.notification_status) {
            case 'sent':
                return 'fa fa-check';
            case 'ready':
                return 'fa fa-clock-o';
            case 'canceled':
                return 'fa fa-trash-o';
            default:
                return 'fa fa-exclamation text-danger';
        }
    }

    /**
     * @returns {string}
     */
    get iconTitle() {
        switch (this.notification.notification_status) {
            case 'sent':
                return this.env._t("Sent");
            case 'ready':
                return this.env._t("Awaiting Dispatch");
            case 'canceled':
                return this.env._t("Canceled");
            default:
                return this.env._t("Error");
        }
    }

    /**
     * @returns {SnailmailNotificationPopoverContentView}
     */
    get snailmailNotificationPopoverContentView() {
        return this.props.record;
    }

    /**
     * @returns {Notification}
     */
    get notification() {
        // Messages from snailmail are considered to have at most one notification.
        return this.snailmailNotificationPopoverContentView.message.notifications[0];
    }

}

Object.assign(SnailmailNotificationPopoverContentView, {
    props: { record: Object },
    template: 'snailmail.SnailmailNotificationPopoverContentView',
});

registerMessagingComponent(SnailmailNotificationPopoverContentView);

