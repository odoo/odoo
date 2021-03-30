odoo.define('snailmail_account.NotificationManager', function (require) {
"use strict";

require('@bus/js/main');

var AbstractService = require('web.AbstractService');
var core = require("web.core");

var SnailmailAccountNotificationManager =  AbstractService.extend({
    /**
     * @override
     */
    start: function () {
        this._super.apply(this, arguments);
        this.env.services['bus.server_communication'].on('snailmail_account.invalid_address', payload => this._handleNotificationInvalidAddress(payload));
    },

    /**
     * @private
     * @param {Object} payload
     * @param {integer} payload.invalid_addresses_count
     */
    _handleNotificationInvalidAddress({ invalid_addresses_count }) {
        const message = _.sprintf(
            this.env._t("%s of the selected partner(s) had an invalid address. The corresponding followups were not sent."),
            owl.utils.escape(invalid_addresses_count),
        );
        this.displayNotification({ message, title: this.env._t("Invalid Addresses") });
    }

});

core.serviceRegistry.add('snailmail_account_notification_service', SnailmailAccountNotificationManager);

return SnailmailAccountNotificationManager;

});
