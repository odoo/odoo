/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class NotificationRequest extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {string}
     */
    getHeaderText() {
        return _.str.sprintf(
            this.env._t("%s has a request"),
            this.messaging.partnerRoot.nameOrDisplayName
        );
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Handle the response of the user when prompted whether push notifications
     * are granted or denied.
     *
     * @private
     * @param {string} value
     */
    _handleResponseNotificationPermission(value) {
        this.messaging.refreshIsNotificationPermissionDefault();
        if (value !== 'granted') {
            this.env.services['bus_service'].sendNotification({
                message: this.env._t("Odoo will not have the permission to send native notifications on this device."),
                title: this.env._t("Permission denied"),
            });
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClick() {
        const windowNotification = this.env.browser.Notification;
        const def = windowNotification && windowNotification.requestPermission();
        if (def) {
            def.then(this._handleResponseNotificationPermission.bind(this));
        }
        if (!this.messaging.device.isMobile) {
            this.messaging.messagingMenu.close();
        }
    }

}

Object.assign(NotificationRequest, {
    props: {},
    template: 'mail.NotificationRequest',
});

registerMessagingComponent(NotificationRequest);
