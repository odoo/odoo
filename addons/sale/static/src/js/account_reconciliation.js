odoo.define('sale.account_reconciliation', function (require) {
"use strict";

var ReconciliationRenderers = require('account.ReconciliationRenderer');
var ReconciliationAction = require('account.ReconciliationClientAction');
var LineRenderer = ReconciliationRenderers.LineRenderer;
var StatementAction = ReconciliationAction.StatementAction;
var core = require('web.core');
var _t = core._t;

LineRenderer.include({
    events: _.extend(
        {},
        LineRenderer.prototype.events, 
        {'click .accounting_view caption .js_open_so': '_onOpenSaleOrder'}
    ),

    _onOpenSaleOrder: function (event) {
        event.preventDefault();
        this.trigger_up('open_sale_orders');
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
                view_type: "list",
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