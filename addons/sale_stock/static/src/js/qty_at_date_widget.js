odoo.define('sale_stock.QtyAtDateWidget', function (require) {
"use strict";

var core = require('web.core');
var QWeb = core.qweb;

var PopoverAbstract = require('stock.PopoverAbstract');
var Context = require('web.Context');
var data_manager = require('web.data_manager');
var widget_registry = require('web.widget_registry');

var _t = core._t;
var time = require('web.time');

var QtyAtDateWidget = PopoverAbstract.extend({
    icon: 'fa fa-info-circle',
    title: _t('Availability'),
    trigger: 'focus',
    placement: 'left',
    color: 'text-primary',
    popoverTemplate: 'sale_stock.QtyDetailPopOver',

    _willRender: function () {
        this.hide = !this.data.display_qty_widget;
        if(this.data.virtual_available_at_date < this.data.qty_to_deliver && !this.data.is_mto) {
            this.color = 'text-danger';
        } else {
            this.color = 'text-primary';
        }
    },

    _setPopOver: function () {
        if(!this.data.scheduled_date) {
            return;
        }
        this.data.delivery_date = this.data.scheduled_date.clone().add(this.getSession().getTZOffset(this.data.scheduled_date), 'minutes').format(time.getLangDateFormat());
        this.data.delivery_date_grid = this.data.scheduled_date.clone().add(this.getSession().getTZOffset(this.data.scheduled_date), 'minutes').format('YYYY-MM-DD');

        this._super();

        var self = this;
        this.$popover.find('.action_open_forecast').on('click', function(ev) {
            ev.stopPropagation();
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
                    args: [[self.data.product_id.data.id]]
                }).then(function (res) {
                    var additional_context = {};
                    additional_context.grid_anchor = self.data.delivery_date_grid;
                    additional_context.search_default_warehouse_id = [self.data.warehouse_id.data.id];
                    additional_context.search_default_below_warehouse = false;
                    action.context = new Context(action.context, additional_context);
                    action.domain = [
                        ['product_id', 'in', res]
                    ];
                    self.do_action(action);
                });
            });
        });
    },
});

widget_registry.add('qty_at_date_widget', QtyAtDateWidget);

return QtyAtDateWidget;
});
