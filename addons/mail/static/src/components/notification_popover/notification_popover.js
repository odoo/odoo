odoo.define('mail/static/src/components/notification_popover/notification_popover.js', function (require) {
'use strict';

const useModels = require('mail/static/src/component_hooks/use_models/use_models.js');

const { Component } = owl;

class NotificationPopover extends Component {

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
            case 'bounce':
                return 'fa fa-exclamation';
            case 'exception':
                return 'fa fa-exclamation';
            case 'ready':
                return 'fa fa-send-o';
            case 'canceled':
                return 'fa fa-trash-o';
        }
        return '';
    }

    /**
     * @returns {string}
     */
    get iconTitle() {
        switch (this.notification.__mfield_notification_status(this)) {
            case 'sent':
                return this.env._t("Sent");
            case 'bounce':
                return this.env._t("Bounced");
            case 'exception':
                return this.env._t("Error");
            case 'ready':
                return this.env._t("Ready");
            case 'canceled':
                return this.env._t("Canceled");
        }
        return '';
    }

    /**
     * @returns {mail.notification[]}
     */
    get notifications() {
        return this.props.notificationLocalIds.map(
            notificationLocalId => this.env.models['mail.notification'].get(notificationLocalId)
        );
    }

}

Object.assign(NotificationPopover, {
    props: {
        notificationLocalIds: {
            type: Array,
            element: String,
        },
    },
    template: 'mail.NotificationPopover',
});

return NotificationPopover;

});
