odoo.define('web.Notification', function (require) {
"use strict";

var Widget = require('web.Widget');

var Notification = Widget.extend({
    template: 'Notification',
    init: function() {
        this._super.apply(this, arguments);
    },
    start: function() {
        this._super.apply(this, arguments);
    },
    notify: function(title, text, sticky) {
        sticky = !!sticky;
        var opts = {};
        if (sticky) {
            opts.expires = false;
        }
        var html = "<b>"+title+"</b><p>"+text+"</p>"
        return this.$el.find('.top-right').notify({ 
            closable: true,
            message: { html: html},
            fadeOut: {enabled: false},
            type: 'info',
        }).show();
    },
    warn: function(title, text, sticky) {
        sticky = !!sticky;
        var opts = {};
        if (sticky) {
            opts.expires = false;
        }
        var html = "<i class='fa fa-exclamation-triangle' /><b>"+title+"</b><p>"+text+"</p>"
        return this.$el.find('.top-right').notify({ 
            closable: true,
            message: { html: html},
            fadeOut: {enabled: true},
            type: 'danger',
        }).show()
    }
});

return Notification;

});
