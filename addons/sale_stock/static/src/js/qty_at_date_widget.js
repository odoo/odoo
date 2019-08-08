odoo.define('sale_stock.QtyAtDateWidget', function (require) {
"use strict";

var core = require('web.core');
var QWeb = core.qweb;

var Widget = require('web.Widget');
var Context = require('web.Context');
var Dialog = require('web.Dialog');
var data_manager = require('web.data_manager');
var widget_registry = require('web.widget_registry');

var _t = core._t;
var time = require('web.time');

var QtyAtDateWidget = Widget.extend({
    template: 'sale_stock.qtyAtDate',
    events: _.extend({}, Widget.prototype.events, {
        'click .fa-info-circle': '_onClickButton',
    }),

    /**
     * @override
     * @param {Widget|null} parent
     * @param {Object} params
     */
    init: function (parent, params) {
        this.data = params.data;
        this._super(parent);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    _onClickButton: function (ev) {
        ev.stopPropagation();
        var self = this;
        this.data.delivery_date = this.data.scheduled_date.clone().add(this.getSession().getTZOffset(this.data.scheduled_date), 'minutes').format(time.getLangDateFormat());
        // The grid view need a specific date format that could be different than
        // the user one.
        this.data.delivery_date_grid = this.data.scheduled_date.clone().add(this.getSession().getTZOffset(this.data.scheduled_date), 'minutes').format('YYYY-MM-DD');
        var $content = $(QWeb.render('sale_stock.QtyDetailDialog', {
            data: this.data,
        }));
        this.dialog = new Dialog(this, {
            size: 'medium',
            title: _.str.sprintf(_t('%s Availability'), self.data.product_id.data.display_name),
            $content: $content,
            buttons: [{
                text: _t('Close'),
                classes: 'btn-primary',
                close: true,
            }],
        });
        this.dialog.opened().then(function () {
            var $forecastButton = self.dialog.$('.action_open_forecast');
            $forecastButton.on('click', function(ev) {
                ev.stopPropagation();
                data_manager.load_action('stock.report_stock_quantity_action').then(function (action) {
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
                        additional_context.search_default_warehouse_id = [self.data.warehouse_id.data.id]
                        action.context = new Context(action.context, additional_context);
                        action.domain = [
                            ['product_id', 'in', res]
                        ];
                        self.do_action(action);
                    });
                });
            });
        });
        this.dialog.open();
    },
});

widget_registry.add('qty_at_date_widget', QtyAtDateWidget);

return QtyAtDateWidget;
});
