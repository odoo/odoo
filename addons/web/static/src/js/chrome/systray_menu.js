odoo.define('web.SystrayMenu', function (require) {
"use strict";

var Widget = require('web.Widget');

/**
 * The SystrayMenu is the class that manage the list of icons in the top right
 * of the menu bar.
 */
var SystrayMenu = Widget.extend({
    /**
     * This widget renders the systray menu. It creates and renders widgets
     * pushed in instance.web.SystrayItems.
     */
    init: function (parent) {
        this._super(parent);
        this.items = [];
        this.widgets = [];
        this.load = $.Deferred();
    },
    /**
     * @override
     * @returns {Deferred}
     */
    start: function () {
        var self = this;
        self._super.apply(this, arguments);
        self._loadItems();
        $.when.apply($, self.items).always(function () {
            self.load.resolve();
        });
        return self.load;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Instantiate items, using the classes located in SystrayMenu.items.
     */
    _loadItems: function () {
        var self = this;
        SystrayMenu.Items = _.sortBy(SystrayMenu.Items, function (item) {
            return !_.isUndefined(item.prototype.sequence) ? item.prototype.sequence : 50;
        });
        _.each(SystrayMenu.Items, function (WidgetClass) {
            var cur_systray_item = new WidgetClass(self);
            self.widgets.push(cur_systray_item);
            self.items.push(cur_systray_item.prependTo(self.$el));
        });
    },
});

SystrayMenu.Items = [];

return SystrayMenu;

});

