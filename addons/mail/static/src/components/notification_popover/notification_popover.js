/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class NotificationPopover extends Component {

    /**
     * @returns {string}
     */
    get iconClass() {
        switch (this.notification.notification_status) {
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
        switch (this.notification.notification_status) {
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
        if (!this.messaging) {
            return [];
        }
        return this.props.notificationLocalIds.map(
            notificationLocalId => this.messaging.models['mail.notification'].get(notificationLocalId)
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

registerMessagingComponent(NotificationPopover, { propsCompareDepth: { notificationLocalIds: 1 } });
