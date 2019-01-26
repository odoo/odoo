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

    _onNotification: function (notifs) {
        var self = this;
        _.each(notifs, function (notif) {
            var model = notif[0][1];
            var type = notif[1].type;
            if (model === 'res.partner' && type === 'snailmail_invalid_address') {
                self.do_warn(notif[1].title,  notif[1].message);
            }
        });
    }

});

core.serviceRegistry.add('snailmail_account_notification_service', SnailmailAccountNotificationManager);

return SnailmailAccountNotificationManager;

});
