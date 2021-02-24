odoo.define('snailmail_account.NotificationManager', function (require) {
"use strict";

var AbstractService = require('web.AbstractService');
var core = require("web.core");

var SnailmailAccountNotificationManager =  AbstractService.extend({
    dependencies: ['bus_service'],

    /**
     * @override
     */
    start: function () {
        this._super.apply(this, arguments);
        this.call('bus_service', 'addListener', notifications => this._handleNotifications(notifications));
    },

    /**
     * @private
     * @param {Object[]} notifications
     * @param {any} [notifications[].payload]
     * @param {string} notifications[].type
     */
    _handleNotifications(notifications) {
        const { _t } = owl.Component.env;
        for (const { payload, type } of notifications) {
            if (type === 'snailmail_account.invalid_address') {
                const { invalid_addresses_count } = payload;
                const message = _.sprintf(
                    _t("%s of the selected partner(s) had an invalid address. The corresponding followups were not sent."),
                    owl.utils.escape(invalid_addresses_count),
                );
                this.displayNotification({ message, title: _t("Invalid Addresses") });
            }
        }
    }

});

core.serviceRegistry.add('snailmail_account_notification_service', SnailmailAccountNotificationManager);

return SnailmailAccountNotificationManager;

});
