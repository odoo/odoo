odoo.define('stock.stock_availability_popover', function (require) {
'use strict';

let PopoverWidget = require('stock.popover_widget');
let fieldRegistry = require('web.field_registry');
let data_manager = require('web.data_manager');
let Context = require('web.Context');
let core = require('web.core');
let _t = core._t;

let StockAvailabilityPopover = PopoverWidget.extend({
    popoverTemplate: 'stock.availabilityPopover',
    title: _t('Product Availability'),
    icon: 'fa-exclamation-triangle',
    color: 'text-warning',


    _render: function () {
        this._super.apply(this, arguments);
        let self = this;
        if (this.$popover) {
            this.$popover.find('.action_open_forecast').click(function (e) {
                self._onOpenForecast(e);
            });
        }
    },

    _onOpenForecast: function (ev) {
        ev.stopPropagation();
        let self = this;
        data_manager.load_action('stock.report_stock_quantity_action_product').then(function (action) {
            // Change action context to choose a specific date and product(s)
            // As grid_anchor is set to now() by default in the data, we need
            // to load the action first, change the context then launch it via do_action
            // additional_context cannot replace a context value, only add new
            //
            // in case of kit product, the forecast view show the kit's components
            self._rpc({
                model: 'product.product',
                method: 'get_components',
                args: [self.value.products.map(p => p[1])]
            }).then( function (res) {
                let additional_context = {};
                additional_context.grid_anchor = self.value.date;
                additional_context.search_default_warehouse_id = [self.value.warehouse];
                action.context = new Context(action.context, additional_context);
                action.domain = [
                    ['product_id', 'in', res]
                ];
                self.do_action(action);
            });
        });
    },
});
fieldRegistry.add('stock_availability_popover', StockAvailabilityPopover);

return StockAvailabilityPopover;
});
