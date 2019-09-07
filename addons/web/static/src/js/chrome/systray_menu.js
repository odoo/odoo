odoo.define('web.SystrayMenu', function (require) {
"use strict";

var dom = require('web.dom');
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
    },
    /**
     * Instanciate the items and add them into a temporary fragmenet
     * @override
     */
    willStart: function () {
        var self = this;
        var proms = [];
        SystrayMenu.Items = _.sortBy(SystrayMenu.Items, function (item) {
            return !_.isUndefined(item.prototype.sequence) ? item.prototype.sequence : 50;
        });

        SystrayMenu.Items.forEach(function (WidgetClass) {
            var cur_systray_item = new WidgetClass(self);
            self.widgets.push(cur_systray_item);
            proms.push(cur_systray_item.appendTo($('<div>')));
        });

        return this._super.apply(this, arguments).then(function () {
            return Promise.all(proms);
        });
    },
    /**
     * Add the instanciated items, using the object located in this.wisgets
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.widgets.forEach(function (widget) {
                dom.prepend(self.$el, widget.$el);
            });
        });
    },
});

SystrayMenu.Items = [];

return SystrayMenu;

});

