odoo.define('web.SystrayMenu', function (require) {
"use strict";

const { ComponentWrapper, WidgetAdapterMixin } = require("web.OwlCompatibility");
var dom = require('web.dom');
const utils = require("web.utils");
var Widget = require('web.Widget');

/**
 * The SystrayMenu is the class that manage the list of icons in the top right
 * of the menu bar.
 */
var SystrayMenu = Widget.extend(WidgetAdapterMixin, {
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
            let curSystrayItem;
            if (utils.isComponent(WidgetClass)) {
                curSystrayItem = new ComponentWrapper(self, WidgetClass, {});
                proms.push(curSystrayItem.mount($("<div>")[0]));
            } else {
                curSystrayItem = new WidgetClass(self);
                proms.push(curSystrayItem.appendTo($("<div>")));
            }
            self.widgets.push(curSystrayItem);
        });

        return this._super.apply(this, arguments).then(function () {
            return Promise.all(proms);
        });
    },
    on_attach_callback() {
        this.widgets
            .filter((widget) => widget.on_attach_callback)
            .forEach((widget) => widget.on_attach_callback());
        WidgetAdapterMixin.on_attach_callback.call(this);
    },
    destroy: function () {
        WidgetAdapterMixin.destroy.call(this);
        this._super();
    },
    /**
     * Add the instanciated items, using the object located in this.wisgets
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.widgets.forEach(function (widget) {
                if (utils.isComponent(widget.constructor)) {
                    dom.prepend(self.$el, $(widget.el));
                } else {
                    dom.prepend(self.$el, widget.$el);
                }
            });
        });
    },
});

SystrayMenu.Items = [];

return SystrayMenu;

});

