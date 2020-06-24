odoo.define('stock.popover_widget', function (require) {
'use strict';

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var QWeb = core.qweb;
var Context = require('web.Context');
var data_manager = require('web.data_manager');
var fieldRegistry = require('web.field_registry');

/**
 * Widget Popover for JSON field (char), by default render a simple html message
 * {
 *  'msg': '<CONTENT OF THE POPOVER>',
 *  'icon': '<FONT AWESOME CLASS>' (optionnal),
 *  'color': '<COLOR CLASS OF ICON>' (optionnal),
 *  'title': '<TITLE OF POPOVER>' (optionnal),
 *  'popoverTemplate': '<TEMPLATE OF THE TEMPLATE>' (optionnal)
 * }
 */
var PopoverWidgetField = AbstractField.extend({
    supportedFieldTypes: ['char'],
    buttonTemplape: 'stock.popoverButton',
    popoverTemplate: 'stock.popoverContent',
    trigger: 'focus',
    placement: 'top',
    html: true,
    color: 'text-primary',
    icon: 'fa-info-circle',

    _render: function () {
        var value = JSON.parse(this.value);
        if (!value) {
            this.$el.html('');
            return;
        }
        this.$el.css('max-width', '17px');
        this.$el.html(QWeb.render(this.buttonTemplape, _.defaults(value, {color: this.color, icon: this.icon})));
        this.$el.find('a').prop('special_click', true);
        this.$popover = $(QWeb.render(value.popoverTemplate || this.popoverTemplate, value));
        this.$popover.on('click', '.action_open_forecast', this._openForecast.bind(this));
        this.$el.find('a').popover({
            content: this.$popover,
            html: this.html,
            placement: this.placement,
            title: value.title || this.title,
            trigger: this.trigger,
            delay: {'show': 0, 'hide': 100},
        });
    },

    /**
     * Redirect to the product graph view.
     * (Based off of qty_at_date_widget.js method)
     *
     * @private
     * @param {MouseEvent} event
     * @returns {Promise} action loaded
     */
    async _openForecast(ev) {
        ev.stopPropagation();
        // Change action context to choose a specific date and product(s)
        // As grid_anchor is set to now() by default in the data, we need
        // to load the action first, change the context then launch it via do_action
        // additional_context cannot replace a context value, only add new
        const action = await data_manager.load_action('stock.report_stock_quantity_action_product');
        const additional_context = {
            grid_anchor: this.recordData.delivery_date_grid,
            search_default_warehouse_id: [this.recordData.warehouse_id.data.id],
            search_default_below_warehouse: false
        };
        action.context = new Context(action.context, additional_context);
        action.domain = [
            ['product_id', '=', this.recordData.product_id.data.id]
        ];
        return this.do_action(action);
    },

    destroy: function () {
        this.$el.find('a').popover('dispose');
        this._super.apply(this, arguments);
    },

});

fieldRegistry.add('popover_widget', PopoverWidgetField);

return PopoverWidgetField;
});
