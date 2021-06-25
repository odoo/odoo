/** @odoo-module **/

import { useShouldUpdateBasedOnProps } from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import { useStore } from '@mail/component_hooks/use_store/use_store';

import { browser } from '@web/core/browser/browser';

const { Component } = owl;

export class NotificationAlert extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useStore(props => {
            const isMessagingInitialized = this.env.services.messaging.isMessagingInitialized();
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
        if (!this.env.services.messaging.isMessagingInitialized()) {
            return false;
        }
        return (
            browser.Notification &&
            browser.Notification.permission !== "granted" &&
            !this.env.services.messaging.messaging.isNotificationPermissionDefault
        );
    }

}

Object.assign(NotificationAlert, {
    props: {},
    template: 'mail.NotificationAlert',
});
