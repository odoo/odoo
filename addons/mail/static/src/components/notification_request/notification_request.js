odoo.define('mail/static/src/components/notification_request/notification_request.js', function (require) {
'use strict';

const components = {
    PartnerImStatusIcon: require('mail/static/src/components/partner_im_status_icon/partner_im_status_icon.js'),
};
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

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
                partnerRoot: this.env.messaging.partnerRoot
                    ? this.env.messaging.partnerRoot.__state
                    : undefined,
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
            this.env.services['bus_service'].sendNotification(
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
        const windowNotification = this.env.browser.Notification;
        const def = windowNotification && windowNotification.requestPermission();
        if (def) {
            def.then(this._handleResponseNotificationPermission.bind(this));
        }
        if (!this.env.messaging.device.isMobile) {
            this.env.messaging.messagingMenu.close();
        }
    }

}

Object.assign(NotificationRequest, {
    components,
    props: {},
    template: 'mail.NotificationRequest',
});

return NotificationRequest;

});
