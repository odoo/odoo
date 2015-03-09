odoo.define('web.Notification', ['web.Widget'], function (require) {
"use strict";

var Widget = require('web.Widget');

var Notification = Widget.extend({
    template: 'Notification',
    init: function() {
        this._super.apply(this, arguments);
    },
    start: function() {
        this._super.apply(this, arguments);
        this.$el.notify({
            speed: 500,
            expires: 2500
        });
    },
    notify: function(title, text, sticky) {
        sticky = !!sticky;
        var opts = {};
        if (sticky) {
            opts.expires = false;
        }
        return this.$el.notify('create', {
            title: title,
            text: text
        }, opts);
    },
    warn: function(title, text, sticky) {
        sticky = !!sticky;
        var opts = {};
        if (sticky) {
            opts.expires = false;
        }
        return this.$el.notify('create', 'oe_notification_alert', {
            title: title,
            text: text
        }, opts);
    }
});

return Notification;

});
