odoo.define('mail_bot.messaging.component.NotificationRequest', function (require) {
'use strict';

const components = {
    PartnerImStatusIcon: require('mail.messaging.component.PartnerImStatusIcon'),
};
const useStore = require('mail.messaging.component_hook.useStore');

const { Component } = owl;

class NotificationRequest extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            return {
                isDeviceMobile: this.env.messaging.device.isMobile,
                partnerRoot: this.env.messaging.partnerRoot,
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {string}
     */
    getHeaderText() {
        return _.str.sprintf(
            this.env._t("%s has a request"),
            this.env.messaging.partnerRoot.nameOrDisplayName
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
        // manually force recompute because the permission is not in the store
        this.env.messaging.messagingMenu.update();
        if (value !== 'granted') {
            this.env.call('bus_service', 'sendNotification',
                this.env._t("Permission denied"),
                this.env._t("Odoo will not have the permission to send native notifications on this device.")
            );
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClick() {
        const windowNotification = this.env.window.Notification;
        const def = windowNotification && windowNotification.requestPermission();
        if (def) {
            def.then(this._handleResponseNotificationPermission.bind(this));
        }
        this.trigger('o-odoobot-request-clicked');
    }

}

Object.assign(NotificationRequest, {
    components,
    props: {},
    template: 'mail_bot.messaging.component.NotificationRequest',
});

return NotificationRequest;

});
