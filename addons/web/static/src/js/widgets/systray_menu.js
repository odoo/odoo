odoo.define('web.SystrayMenu', function (require) {
"use strict";

var Widget = require('web.Widget');

var SystrayMenu = Widget.extend({
    /**
     * This widget renders the systray menu. It creates and renders widgets
     * pushed in instance.web.SystrayItems.
     */
    init: function(parent) {
        this._super(parent);
        this.items = [];
        this.load = $.Deferred();
    },
    start: function() {
        var self = this;
        self._super.apply(this, arguments);
        self.load_items();
        return $.when.apply($, self.items).done(function () {
            self.load.resolve();
        });
    },
    load_items: function() {
        var self = this;
        _.each(SystrayMenu.Items, function(widgetCls) {
            var cur_systray_item = new widgetCls(self);
            self.items.push(cur_systray_item.appendTo(self.$el));
        });
    },
});

SystrayMenu.Items = [];

return SystrayMenu;

});

