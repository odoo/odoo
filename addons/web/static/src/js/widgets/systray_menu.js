odoo.define('web.SystrayMenu', function (require) {
"use strict";

var Widget = require('web.Widget');
var Items = [];
var ItemsEvent = $({});

var SystrayMenu = Widget.extend({
    /**
     * This widget renders the systray menu. It creates and renders widgets
     * pushed in instance.web.SystrayItems.
     */
    init: function(parent) {
        this._super(parent);
        this.items = [];
        this.widgets = [];
        this.load = $.Deferred();
    },
    start: function() {
        var self = this;
        self._super.apply(this, arguments);
        self.load_items();
        $.when.apply($, self.items).always(function () {
            self.load.resolve();
        });
        return self.load;
    },
    load_items: function() {
        var self = this;
        Items = _.sortBy(Items, function (item) {
            return !_.isUndefined(item.prototype.sequence) ? item.prototype.sequence : 50;
        });
        
        function add (widgetCls) {
            var cur_systray_item = new widgetCls(self);
            self.widgets.push(cur_systray_item);
            self.items.push(cur_systray_item.appendTo(self.$el));
        }
        _.each(Items, add);
        ItemsEvent.on('add', function (e, widgetCls) {add(widgetCls);});
    },
});

SystrayMenu.add = function (Widget) {
    Items.push(Widget);
    ItemsEvent.trigger('add', Widget);
};

return SystrayMenu;

});

