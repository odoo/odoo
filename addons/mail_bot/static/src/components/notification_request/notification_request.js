odoo.define('mail_bot/static/src/components/notification_request/notification_request.js', function (require) {
'use strict';

const components = {
    PartnerImStatusIcon: require('mail/static/src/components/partner_im_status_icon/partner_im_status_icon.js'),
};
const useModels = require('mail/static/src/component_hooks/use_models/use_models.js');

const { Component } = owl;

class NotificationRequest extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useModels();
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
            this.env.messaging.__mfield_partnerRoot(this).__mfield_nameOrDisplayName(this)
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
        this.env.messaging.__mfield_messagingMenu(this).update();
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
        if (!this.env.messaging.__mfield_device(this).__mfield_isMobile(this)) {
            this.env.messaging.__mfield_messagingMenu(this).close();
        }
    }

}

Object.assign(NotificationRequest, {
    components,
    props: {},
    template: 'mail_bot.NotificationRequest',
});

return NotificationRequest;

});
