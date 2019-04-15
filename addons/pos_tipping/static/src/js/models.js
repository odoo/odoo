odoo.define("pos_tipping.models", function(require) {
"use strict";
var core = require("web.core");
var utils = require("web.utils");
var models = require("point_of_sale.models");
var field_utils = require("web.field_utils");

var _t = core._t;
var round_pr = utils.round_precision;

models.load_models({
    model: "pos.order",
    fields: [
        "pos_reference",
        "amount_total",
        "date_order",
        "tip_amount",
        "is_tipped",
        "is_tippable",
        "is_being_captured",
        "partner_name",
        "table_name"
    ],
    order: [{ name: "date_order" }],
    domain: function(self) {
        return [["session_id", "=", self.pos_session.id]];
    },
    loaded: function(self, orders) {
        orders.forEach(function(order) {
            if (!order.is_tippable) {
                return;
            }
            self.db.insert_validated_order({
                uid: order.pos_reference.replace(_t("Order "), ""),
                amount_total: order.amount_total,

                // mimic _symbol_set
                amount_total_without_tip: parseFloat(
                    round_pr(order.amount_total - order.tip_amount, self.currency.rounding).toFixed(
                        self.currency.decimals
                    )
                ),

                tip_amount: order.tip_amount,
                is_tipped: order.is_tipped || order.is_being_captured,
                tip_is_finalized: order.is_tipped || order.is_being_captured,
                is_tippable: order.is_tippable,
                creation_date: field_utils.format.datetime(moment(order.date_order), {}, { timezone: false }),
                partner_name: order.partner_name,
                table: order.table_name
            });
        });
    }
});

var _super_order = models.Order.prototype;
models.Order = models.Order.extend({
    initialize: function() {
        _super_order.initialize.apply(this, arguments);
        this.is_tipped = false;
    },

    init_from_JSON: function(json) {
        _super_order.init_from_JSON.apply(this, arguments);
        this.authorization_payment_method = this.pos.payment_methods_by_id[json.authorization_payment_method_id];
        this.authorization_id = json.authorization_id;
    },

    export_as_JSON: function() {
        var res = _super_order.export_as_JSON.apply(this, arguments);
        var tip = this.get_tip();

        return _.extend(res, {
            tip_amount: tip,
            is_tipped: tip > 0,
            is_tippable: !this.is_paid_with_cash(),
            authorization_payment_method_id: this.authorization_payment_method && this.authorization_payment_method.id,
            authorization_id: this.authorization_id,
        });
    },

    export_for_printing: function() {
        var receipt = _super_order.export_for_printing.apply(this, arguments);
        var used_non_cash = _.any(this.get_paymentlines(), function (line) {
            return !line.payment_method.is_cash_count;
        });
        receipt.print_tip = this.pos.config.handle_tip_adjustments && used_non_cash;
        return receipt;
    },
});

});
