odoo.define('account_reconcile_sale_order.reconciliation_custom', function (require) {
"use strict";

var Model = require('web.Model');
var form_common = require('web.form_common');
var reconciliation_widgets = require('account.reconciliation');
var core = require('web.core');
var _ = require('_');
var _t = core._t;
var SelectCreateDialog = form_common.SelectCreateDialog;
var QWeb = core.qweb;

reconciliation_widgets.bankStatementReconciliationLine.include({
    events: _.defaults({
        "click .create_counter_part_so": "createCounterPartSO",
        "click .go_to_so": "goToSO",
    }, reconciliation_widgets.bankStatementReconciliationLine.prototype.events),

    init: function() {
        var self = this;
        this._super.apply(this, arguments);
        // The first widget that requires the action to open a sale order stores that action
        // in its parent (the client action), so when the user wants to open a reconciliation's
        // matched sale order, we just reuse the action and change its res_id.
        var parent = this.getParent();
        if (!parent.action_open_sale_order && this.init_data && this.init_data.sale_orders) {
            new Model("ir.actions.act_window")
                .call("for_xml_id", ['account_reconcile_sale_order', 'action_sale_order'])
                .done(function(action) { parent.action_open_sale_order = action })
                .fail(function() { self.do_warn(_t("Oops, we encountered an error. Please reload the page.")) });
        }
    },

    createCounterPartSO: function(e) {
        var self = this;
        // Prevent the widget from going to 'match' mode
        e.stopPropagation();
        new Model("account.bank.statement.line").call("so_counterpart_creation", [[self.st_line.id], $(e.target).data('sale_order_id')]).then(function (result) {
            var $link_to_so = $(QWeb.render("bank_statement_reconciliation_line_link_to_so", {so_id: $(e.target).data('sale_order_id')}));
            $(e.target).parents('div.so-selection').after($link_to_so);
        });
    },

    goToSO: function(e) {
        var self = this;
        // Prevent the widget from going to 'match' mode
        var action = self.getParent().action_open_sale_order;
        action.res_id = $(e.target).data('so_id');
        self.do_action(action);
    },

    openSaleOrder: function(e) {
        var self = this;
        // Prevent the widget from going to 'match' mode
        e.stopPropagation();

        new SelectCreateDialog(this, {
            res_model: 'sale.order',
            context: {search_default_partner_id: [this.init_data.line.partner_id], search_default_sent_or_sale: 1},
            title: _t("Select a sale order"),
            initial_view: "search",
            disable_multiple_selection: true,
            no_create: true,
            on_selected: function(element_ids) {
                var action = self.getParent().action_open_sale_order;
                action.res_id = element_ids[0];
                // When the user comes back, after possibly having generated an invoice for the sale order,
                // select the reconciliable move lines from the sale order's invoice(s) which are not already
                // selected or selected elsewhere.
                self.do_action(action, { on_reverse_breadcrumb: function() {
                    new Model("sale.order")
                        .call("get_move_lines_for_reconciliation_widget", [element_ids[0], self.st_line.id])
                        .then(function(lines) {
                            if (lines.length === 0) {
                                self.do_warn(_t("There is no open invoice for the sale order."));
                                return;
                            }
                            // Filter out lines already selected (here or in another reconciliation)
                            var excluded_ids = _.reduce(self.getParent().excluded_move_lines_ids, function(memo, val) { return memo.concat(val) }, []);
                            lines = _.filter(lines, function(line) { return excluded_ids.indexOf(line.id) === -1 });
                            // Remove from mv_lines_deselected the lines we are about to select
                            var line_ids = _.map(lines, function(line) { return line.id });
                            self.mv_lines_deselected = _.filter(self.mv_lines_deselected, function(line){ return line_ids.indexOf(line.id) === -1 });
                            // Put the SO's reconciliable invoice lines in the selected lines, without duplicate
                            var mv_lines_selected = _.uniq(_.union(self.get("mv_lines_selected"), lines), false, _.property('id'));
                            _.each(lines, function(line) { self.decorateMoveLine(line) }, self);
                            self.set("mv_lines_selected", mv_lines_selected);
                        });
                    },
                });
            }
        }).open();
    },
});

});
