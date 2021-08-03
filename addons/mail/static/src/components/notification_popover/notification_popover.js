/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models/use_models';
import { useShouldUpdateBasedOnProps } from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';

const { Component } = owl;

export class NotificationPopover extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps({
            compareDepth: {
                notificationLocalIds: 1,
            },
        });
        useModels();
    }

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
