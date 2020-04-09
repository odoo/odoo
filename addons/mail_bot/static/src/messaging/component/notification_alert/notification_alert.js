odoo.define('mail_bot.messaging.component.NotificationAlert', function (require) {
'use strict';

const useStore = require('mail.messaging.component_hook.useStore');

const { Component } = owl;

class NotificationAlert extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const isMessagingInitialized = this.env.isMessagingInitialized();
            return {
                isMessagingInitialized,
                isNotificationBlocked: this.isNotificationBlocked,
            };
        });
    }

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
        const windowNotification = this.env.window.Notification;
        return (
            windowNotification &&
            windowNotification.permission !== "granted" &&
            !this.env.messaging.constructor.isNotificationPermissionDefault()
        );
    }

}

Object.assign(NotificationAlert, {
    props: {},
    template: 'mail_bot.messaging.component.NotificationAlert',
});

return NotificationAlert;

});
