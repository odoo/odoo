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
        this.call('bus_service', 'onNotification', this, this._onNotification);
    },

    _onNotification: function(notifications) {
        for (const { payload, type } of notifications) {
            if (type === "snailmail_invalid_address") {
                this.displayNotification({ title: payload.title, message: payload.message, type: 'danger' });
            }
        }
    }

});

core.serviceRegistry.add('snailmail_account_notification_service', SnailmailAccountNotificationManager);

return SnailmailAccountNotificationManager;

});
