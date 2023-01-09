odoo.define('snailmail_account.NotificationManager', function (require) {
"use strict";

var AbstractService = require('web.AbstractService');
var core = require("web.core");

var SnailmailAccountNotificationManager =  AbstractService.extend({
    /**
     * @override
     */
    start: function () {
        this._super.apply(this, arguments);
        core.bus.on('web_client_ready', null, () => {
            this.call('bus_service', 'addEventListener', 'notification', this._onNotification.bind(this));
        });
    },

    _onNotification: function({ detail: notifications }) {
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
