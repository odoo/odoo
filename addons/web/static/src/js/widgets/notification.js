odoo.define('web.notification', function (require) {
"use strict";

var Widget = require('web.Widget');

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
    /**
     * @override
     */
    start: function () {
        this.$el.addClass('o_error');
        return this._super.apply(this, arguments);
    },
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

return {
    Notification: Notification,
    Warning: Warning,
    NotificationManager: NotificationManager,
};

});
