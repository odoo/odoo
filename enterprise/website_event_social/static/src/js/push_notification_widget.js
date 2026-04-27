/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import NotificationWidget from "@social_push_notifications/js/push_notification_widget";

NotificationWidget.include({
    /**
     * Basic override that forces the display of the popup, ignoring the expirationDate for the
     * tickets registration confirmation page.
     */
    _askPermission: function () {
        var self = this;

        if (!document.querySelector(".o_wereg_js_confirmed")) {
            return this._super(...arguments);
        }

        this._fetchPushConfiguration().then(function (config) {
            self._showNotificationRequestPopup({
                title: config.notification_request_title,
                body: config.notification_request_body,
                delay: config.notification_request_delay,
                icon: config.notification_request_icon
            }, config);
        });
    },

    /**
     * Basic override that forces the title, body and delay of the popup if we are
     * on the registration confirmed page.
     */
    _showNotificationRequestPopup: function (popupConfig, pushConfig) {
        if (!document.querySelector(".o_wereg_js_confirmed")) {
            return this._super(...arguments);
        }

        if (popupConfig.title && popupConfig.body) {
            popupConfig.title = _t('Get the best experience!');
            popupConfig.body = _t('Allow notifications to be able to add talks into your favorite list or connect to other attendees.');
            popupConfig.delay = 0;
        }

        return this._super(popupConfig, pushConfig);
    },
});
