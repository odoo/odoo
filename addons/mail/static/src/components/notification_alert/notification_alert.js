odoo.define('mail/static/src/components/notification_alert/notification_alert.js', function (require) {
'use strict';

const useShouldUpdateBasedOnProps = require('mail/static/src/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props.js');
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;

class NotificationAlert extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
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
        const windowNotification = this.env.browser.Notification;
        return (
            windowNotification &&
            windowNotification.permission !== "granted" &&
            !this.env.messaging.isNotificationPermissionDefault()
        );
    }

}

Object.assign(NotificationAlert, {
    props: {},
    template: 'mail.NotificationAlert',
});

return NotificationAlert;

});
