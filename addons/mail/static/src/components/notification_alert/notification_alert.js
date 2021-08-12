/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class NotificationAlert extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {boolean}
     */
    get isNotificationBlocked() {
        if (!this.env.isMessagingInitialized()) {
            return false;
        }
        const windowNotification = this.env.browser.Notification;
        return (
            windowNotification &&
            windowNotification.permission !== "granted" &&
            !this.env.messaging.isNotificationPermissionDefault
        );
    }

}

Object.assign(NotificationAlert, {
    props: {},
    template: 'mail.NotificationAlert',
});

registerMessagingComponent(NotificationAlert);
