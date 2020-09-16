odoo.define('snailmail/static/src/components/snailmail_notification_popover/snailmail_notification_popover.js', function (require) {
'use strict';

const useModels = require('mail/static/src/component_hooks/use_models/use_models.js');

const { Component } = owl;

class SnailmailNotificationPopover extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useModels();
    }

    /**
     * @returns {string}
     */
    get iconClass() {
        switch (this.notification.__mfield_notification_status(this)) {
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
        switch (this.notification.__mfield_notification_status(this)) {
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
        return this.message.__mfield_notifications(this)[0];
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
