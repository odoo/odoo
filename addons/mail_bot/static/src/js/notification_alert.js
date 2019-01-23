odoo.define('mail.NotificationAlert', function (require) {
"use strict";

var Widget = require('web.Widget');
var widgetRegistry = require('web.widget_registry');

// -----------------------------------------------------------------------------
// Display Notification alert on user preferences form view
// -----------------------------------------------------------------------------
var NotificationAlert = Widget.extend({
   template: 'mail.NotificationAlert',
   /**
    * @override
    */
   init: function () {
      this._super.apply(this, arguments);
      var hasRequest = this.call('mailbot_service', 'isRequestingForNativeNotifications');
      this.isNotificationBlocked = window.Notification && window.Notification.permission !== "granted" && !hasRequest;
   },
});

widgetRegistry.add('notification_alert', NotificationAlert);

return NotificationAlert;

});
