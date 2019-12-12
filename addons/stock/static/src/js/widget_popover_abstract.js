odoo.define('stock.PopoverAbstract', function (require) {
"use strict";

var core = require('web.core');
var QWeb = core.qweb;
var Widget = require('web.Widget');
var widget_registry = require('web.widget_registry');
var _t = core._t;

var PopoverAbstract = Widget.extend({
    template: 'stock.popoverTemplate',

    icon: 'fa fa-info-circle',
    title: '',
    trigger: 'focus',
    placement: 'left',
    color: 'text-primary',
    popoverTemplate: '',
    hide: false,

    events: _.extend({}, Widget.prototype.events, {
        'click .o_html_popover_icon': '_onClickButton',
    }),

    /**
     * @override
     * @param {Widget|null} parent
     * @param {Object} params
     */
    init: function (parent, params) {
        this.data = params.data;
        this._willRender();
        this.viewType = params.viewType;
        this._super(parent);
    },

    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self._setPopOver();
        });
    },

    updateState: function (state) {
        this.$el.find('a').popover('dispose');
        var candidate = state.data[this.getParent().currentRow];
        if (candidate) {
            this.data = candidate.data;
            this._willRender();
            this.renderElement();
            this._setPopOver();
        }
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * Set a bootstrap popover on the current QtyAtDate widget that display available
     * quantity.
     */
    _setPopOver: function () {
        if (!this.popoverTemplate) {
            return;
        }
        this.$popover = $(QWeb.render(this.popoverTemplate, {data: this.data}));
        this.$el.find('a').popover({
            content: this.$popover,
            html: true,
            placement: this.placement,
            title: this.title,
            trigger: this.trigger,
            delay: {'show': 0, 'hide': 100 },
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    _onClickButton: function () {
        // We add the property special click on the widget link.
        // This hack allows us to trigger the popover (see _setPopOver) without
        // triggering the _onRowClicked that opens the order line form view.
        this.$el.find('.o_html_popover_icon').prop('special_click', true);
    },

    /**
     * Call before rendering the icon.
     * Can be used to calculate variable before rendering.
     */
    _willRender: function () {
        // can be inherited
    },
});

return PopoverAbstract;
});
