odoo.define("pos_tipping.DB", function(require) {
"use strict";
var db = require("point_of_sale.DB");
var field_utils = require("web.field_utils");

db.include({
    init: function(options) {
        this._super(options);
        this.confirmed_orders = [];
    },

    insert_validated_order: function(order) {
        var order_to_save = _.pick(
            order,
            "uid",
            "amount_total",
            "amount_total_without_tip",
            "tip_amount",
            "is_tipped",
            "tip_is_finalized",
            "creation_date",
            "partner_name",
            "table"
        );

        // add this to the beginning because the tipping screen
        // shows orders from new to old.
        this.confirmed_orders.unshift(order_to_save);
    },

    // After an order is synced it'll be removed. We save a copy
    // of it for the tipping interface.
    remove_order: function(order_id) {
        var order = this.get_order(order_id);
        if (!order) {
            return this._super(order_id);
        }

        order = order.data;
        if (order.is_tippable) {
            this.insert_validated_order(
                _.extend(order, {
                    amount_total_without_tip: order.amount_total - (order.tip_amount || 0),
                    tip_amount: order.tip_amount || 0,
                    is_tipped: order.is_tipped,
                    tip_is_finalized: order.is_tipped,
                    creation_date: field_utils.format.datetime(
                        moment(order.creation_date),
                        {},
                        { timezone: false }
                    ),
                    partner_name: order.partner_id && this.get_partner_by_id(order.partner_id).name
                })
            );
        }

        return this._super(order_id);
    }
});
});
