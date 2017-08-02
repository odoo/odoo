odoo.define('sale.ReconciliationClientAction', function (require) {
"use strict";

var ReconciliationClientAction = require('account.ReconciliationClientAction');
var core = require('web.core');
var fieldUtils = require('web.field_utils');
var Dialog = require('web.view_dialogs');

var _t = core._t;
var saleOrderSelectViewId;
var saleOrderSearchViewId;


ReconciliationClientAction.StatementAction.include({
    custom_events: _.extend({}, ReconciliationClientAction.StatementAction.prototype.custom_events, {
        reconcile_with_sale_order: '_onReconcileWithSaleOrder',
    }),

    /**
     * @override
     */
    willStart: function () {
        var selectViewDef = !saleOrderSelectViewId && this._rpc({
                model: 'ir.model.data',
                method: 'xmlid_to_res_id',
                kwargs: {xmlid: 'sale.view_sales_order_reconciliation_tree'},
            }).then(function (id) {
                saleOrderSelectViewId = id;
            });
        var searchViewDef = !saleOrderSearchViewId && this._rpc({
                model: 'ir.model.data',
                method: 'xmlid_to_res_id',
                kwargs: {xmlid: 'sale.view_sales_order_reconciliation_filter'},
            }).then(function (id) {
                saleOrderSearchViewId = id;
            });
        return $.when(this._super.apply(this, arguments), selectViewDef, searchViewDef);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {string} handle
     * @param {Object} record
     */
    _openReconcileWithSaleOrderView: function (handle, record) {
        var self = this;
        var domain = [
            ['state', 'in', ['sent', 'sale']],
            ['invoice_status', '!=', 'invoiced']];
        if (record.partner_id) {
            domain.push(['partner_id', '=', record.partner_id]);
        }

        new Dialog.SelectCreateDialog(this, {
            listViewId: saleOrderSelectViewId,
            searchViewId: saleOrderSearchViewId,
            no_create: true,
            readonly: true,
            res_model: 'sale.order',
            domain: domain,
            context: {
                search_default_name: record.ref || record.name,
            },
            buttons: [{
                text: _t("Confirm & Invoice selected Sales Order(s)"),
                classes: "btn-primary o_select_button",
                disabled: true,
                close: true,
                click: function () {
                    this.on_selected(this.list_controller.getSelectedIds());
                },
            }, {
                text: _t("Cancel"),
                classes: "btn-default o_form_button_cancel",
                close: true,
            }],
            on_selected: function (elementIds) {
                self._reconcileWithSaleOrder(handle, record, elementIds);
            },
        }).open();
    },
    /**
     * @private
     * @param {string} handle
     * @param {Object} record
     * @param {int[]} saleOrderIds
     * @return {Deferred}
     */
    _reconcileWithSaleOrder: function (handle, record, saleOrderIds) {
        var self = this;
        var line = this.model.getLine(handle);
        line.blockUI = true;
        this._getWidget(handle).update(line);

        return this._rpc({
            model: 'sale.order',
            method: 'read',
            args: [saleOrderIds, ['name', 'partner_id', 'client_order_ref', 'amount_total', 'currency_id', 'state', 'invoice_ids', 'invoice_status']],
        }).then(function (orders) {
            if (!orders.length) {
                line.blockUI = false;
                self._getWidget(handle).update(line);
                return;
            }

            // check if all sale order is liked to the same partner
            if (_.uniq(_.map(_.pluck(orders, 'partner_id'), _.first)).length !== 1) {
                self._openReconcileWithSaleOrderView(handle, record);
                line.blockUI = false;
                self._getWidget(handle).update(line);
                self.do_warn(_t("It is not possible to reconcile two sale orders with different partners."));
                return;
            }

            // convert quotation in sale order
            var def = $.when();
            var toConfirm = _.pluck(_.where(orders, {state: 'sent'}), 'id');
            if (toConfirm.length) {
                def = self._rpc({
                    model: 'sale.order',
                    method: 'action_confirm',
                    args: [toConfirm],
                });
            }

            return def.then(function () {
                return self._reconcileWithSaleOrderCreateInvoices(handle, record, saleOrderIds, orders)
                    .then(function () {
                    line.blockUI = false;
                    self._getWidget(handle).update(line);
                }).then(function () {
                    var order_ids = _.uniq(_.flatten(_.pluck(self.model.lines, 'order_ids')));
                    return self._rpc({
                        model: 'sale.order',
                        method: 'search',
                        args: [[
                            ['id', 'in', order_ids],
                            ['state', 'in', ['sent', 'sale']],
                            ['invoice_status', '!=', 'invoiced']]],
                    }).then(function (ids) {
                        _.each(self.model.lines, function (line, handle) {
                            if (!line.order_ids.length) {
                                return;
                            }
                            line.order_ids = _.intersection(line.order_ids, ids);
                            if (!line.order_ids.length) {
                                self._getWidget(handle).update(line);
                            }
                        });
                    });
                });
            });
        });
    },
    /**
     * @private
     * @param {string} handle
     * @param {Object} record
     * @param {int[]} saleOrderIds
     * @param {Object[]} record
     * @return {Deferred}
     */
    _reconcileWithSaleOrderCreateInvoices: function (handle, record, saleOrderIds, orders) {
        var self = this;
        var line = this.model.getLine(handle);
        var props = [];
        var defs = _.map(orders, function (order) {
            var def = $.Deferred();
            var amount = fieldUtils.format.monetary(order.amount_total, {}, {currency_id: order.currency_id[0]});
            var dialog = new Dialog.FormViewDialog(self, {
                title: _.str.sprintf(core._t('Invoice Orders: %s (%s) to be reconciled with: %s (%s)'), order.client_order_ref || order.name, amount, record.ref || record.name, record.amount_str),
                type: 'ir.actions.act_window',
                res_model: 'sale.advance.payment.inv',
                view_type: 'form',
                view_mode: 'form',
                target: 'new',
                context: {
                    active_ids: [order.id],
                    default_amount: orders.length === 1 ? (Math.abs(record.amount) <= order.amount_total ? Math.abs(record.amount) : order.amount_total) : null,
                    reconcile_with_sale_order: true
                },
                buttons: [{
                        text: core._t("Create and Validate Invoice"),
                        classes: "btn-primary",
                        click: function () {
                            this._save().always(this.close.bind(this));
                        }
                    }, {
                        text: core._t("Discard"),
                        classes: "btn-default o_form_button_cancel",
                        close: true,
                        click: function () {
                            this.form_view.model.discardChanges(this.form_view.handle, {
                                rollback: this.shouldSaveLocally,
                            });
                        }
                    }
                ],
                on_saved: function (r) {
                    order.saved = true;
                    return self._rpc({
                        model: 'sale.advance.payment.inv',
                        method: 'create_invoices',
                        args: [[r.data.id]],
                        context: {
                            active_ids: [order.id],
                        },
                    }).then(function () {
                        return self._rpc({
                            model: 'sale.order',
                            method: 'read',
                            args: [order.id, ['invoice_ids']],
                        });
                    }, function () {
                        order.saved = false;
                        def.resolve();
                    }).then(function (rec) {
                        var createdInvoices = _.difference(rec[0].invoice_ids, order.invoice_ids);
                        return self._rpc({
                            model: 'account.reconciliation',
                            method: 'reconciliation_create_move_lines_propositions',
                            args: [[order.id], createdInvoices, line.st_line.currency_id]
                        });
                    }).then(function (prop) {
                        props.push.apply(props, prop);
                        def.resolve();
                    });
                }
            });
            dialog.on('closed', self, function () {
                if (!order.saved) {
                    def.resolve();
                }
            });
            dialog.open();
            return def;
        });
        return $.when.apply($, defs)
            .then(function () {
                return self.model.addMultiPropositions(handle, props);
            }).then(function () {
                if (!record.partner_id) {
                    return self.model.changePartner(handle, {
                        id: orders[0].partner_id[0],
                        display_name: orders[0].partner_id[1]
                    });
                }
            });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} event
     */
    _onReconcileWithSaleOrder: function (event) {
        var handle = event.target.handle;
        var line = this.model.getLine(handle);
        this._openReconcileWithSaleOrderView(handle, line.st_line);
    },
});

ReconciliationClientAction.ManualAction.include({

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     */
    _onReconcileWithSaleOrder: function (event) {
        var handle = event.target.handle;
        var line = this.model.getLine(handle);
        var record = _.extend({}, line.reconciliation_proposition[0]);
        if (!record.currency_id) {
            record.currency_id = line.st_line.currency_id;
        }
        this._openReconcileWithSaleOrderView(handle, record);
    },
});

return ReconciliationClientAction;
});
