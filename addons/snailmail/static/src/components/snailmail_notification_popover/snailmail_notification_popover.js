odoo.define('snailmail/static/src/components/snailmail_notification_popover/snailmail_notification_popover.js', function (require) {
'use strict';

const { Component } = owl;
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

class SnailmailNotificationPopover extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const message = this.env.models['mail.message'].get(props.messageLocalId);
            const notifications = message ? message.notifications : [];
            return {
                message: message ? message.__state : undefined,
                notifications: notifications.map(notification => notification ? notification.__state : undefined),
            };
        }, {
            compareDepth: {
                notifications: 1,
            },
        });
    }

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
     * @returns {mail.message}
     */
    get message() {
        return this.env.models['mail.message'].get(this.props.messageLocalId);
    }

    /**
     * @returns {mail.notification}
     */
    get notification() {
        // Messages from snailmail are considered to have at most one notification.
        return this.message.notifications[0];
    }

}

Object.assign(SnailmailNotificationPopover, {
    props: {
        messageLocalId: String,
    },
    template: 'snailmail.SnailmailNotificationPopover',
});

return SnailmailNotificationPopover;

});
