odoo.define('sale.account_reconciliation', function (require) {
"use strict";

var ReconciliationRenderers = require('account.ReconciliationRenderer');
var ReconciliationAction = require('account.ReconciliationClientAction');
var ReconciliationModel = require('account.ReconciliationModel');
var LineRenderer = ReconciliationRenderers.LineRenderer;
var StatementAction = ReconciliationAction.StatementAction;
var core = require('web.core');
var _t = core._t;

LineRenderer.include({
    events: _.extend(
        {},
        LineRenderer.prototype.events,
        {'click .o_notebook .js_open_so': '_onOpenSaleOrder'}
    ),

    _onOpenSaleOrder: function (event) {
        event.preventDefault();
        this.trigger_up('open_sale_orders');
    },

});

ReconciliationModel.StatementModel.include({
    _getDefaultMode: function(handle) {
        var line = this.getLine(handle);
        var ret = this._super(handle)
        if (ret !== 'inactive' && line.sale_order_ids && line.sale_order_ids.length && line.sale_order_prioritize) {
            return 'saleorder'
        } else {
            return ret;
        }
    },
    _getAvailableModes: function(handle) {
        var line = this.getLine(handle);
        var modes = this._super(handle);
        if (line.sale_order_ids && line.sale_order_ids.length && line.sale_order_prioritize) {
            modes.push('saleorder')
        }
        return modes;
    },
});

StatementAction.include({
    custom_events: _.extend(
        {},
        StatementAction.prototype.custom_events,
        {open_sale_orders: '_onOpenSaleOrders',}
    ),

    _onOpenSaleOrders: function(event) {
        var self = this;
        var handle = event.target.handle;
        var line = this.model.getLine(handle);
        if (line.sale_order_ids && line.sale_order_ids.length > 1) {
            // Open tree view
            this.do_action({
                name: _t('Sale Orders'),
                type: 'ir.actions.act_window',
                res_model: 'sale.order',
                views: [[false, 'list'], [false, 'form']],
                view_mode: "list",
                target: 'current',
                domain: [['id', 'in', line.sale_order_ids]]
            },
            {
                on_reverse_breadcrumb: function() {self.trigger_up('reload');},
            });
        }
        else if (line.sale_order_ids && line.sale_order_ids.length === 1) {
            // Open form view
            this.do_action({
                name: _t('Sale Order'),
                type: 'ir.actions.act_window',
                res_model: 'sale.order',
                views: [[false, 'form']],
                target: 'current',
                res_id: line.sale_order_ids[0],
            },
            {
                on_reverse_breadcrumb: function() {self.trigger_up('reload');},
            });
        }
    },
});

})
