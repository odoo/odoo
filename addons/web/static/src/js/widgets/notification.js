odoo.define('web.notification', function (require) {
"use strict";

var core = require('web.core');
var Widget = require('web.Widget');

var _t = core._t;

var Notification = Widget.extend({
    template: 'Notification',
    events: {
        'click .o_close': function(e) {
            e.preventDefault();
            this.destroy(true);
        }
    },
    init: function(parent, title, text, sticky) {
        this._super.apply(this, arguments);
        this.title = title;
        this.text = text;
        this.sticky = !!sticky;
    },
    start: function() {
        this._super.apply(this, arguments);

        var self = this;
        this.$el.animate({opacity: 1.0}, 400, "swing", function() {
            if(!self.sticky) {
                setTimeout(function() {
                    self.destroy(true);
                }, 2500);
            }
        });
    },
    destroy: function(animate) {
        if(!animate) {
            return this._super.apply(this, arguments);
        }

        var self = this, 
            superDestroy = this._super;
        this.$el.animate({opacity: 0.0}, 400, "swing", function() {
            self.$el.animate({height: 0}, 400, "swing", function() {
                superDestroy.call(self);
            });
        });
    },
});

var Warning = Notification.extend({
    template: 'Warning',
});

var NotificationManager = Widget.extend({
    className: 'o_notification_manager',

    display: function(notification) {
        notification.appendTo(this.$el);
        return notification;
    },
    notify: function(title, text, sticky) {
        return this.display(new Notification(this, title, text, sticky));
    },
    warn: function(title, text, sticky) {
        return this.display(new Warning(this, title, text, sticky));
    },
});

var NotificationBar = Widget.extend({
    template: 'NotificationBar',

    events: {
        "click .o_annoying_notification_bar, .fa-close": function () {
            this.$el.slideUp();
        },
        "click .o_request_permission": function (event) {
            event.preventDefault();
            this.on_click_request_permission();
        },
    },
    init: function () {
        this._super.apply(this, arguments);
        this.notification_bar = (window.Notification && window.Notification.permission === "default");
    },
    send_notification: function(title, content) {
        this.do_notify(title, content);
    },
    on_click_request_permission: function () {
        this.$el.slideUp();
        var def = window.Notification.requestPermission();
        var self = this;
        if (def) {
            def.then(function (value) {
                if (value === 'denied') {
                    self.send_notification(_t('Permission denied'), _t('Odoo will not have the permission to send native notifications on this device.'));
                } else {
                    self.send_notification(_t('Permission granted'), _t('Odoo has permission to send you native notifications on this device.'));
                }
            });
        }
    }
});

return {
    Notification: Notification,
    Warning: Warning,
    NotificationManager: NotificationManager,
    NotificationBar: NotificationBar,
};

});
