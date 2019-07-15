odoo.define('pos_deletion.deletion', function (require) {
    var core    = require('web.core');
    var screens = require('point_of_sale.screens');
    var models = require('point_of_sale.models');
    var devices = require('point_of_sale.devices');
    var chrome = require('point_of_sale.chrome');
    var gui = require('point_of_sale.gui');
    var DB = require('point_of_sale.DB');
    var popups = require('point_of_sale.popups');
    var Class = require('web.Class');
    var utils = require('web.utils');
    var PosBaseWidget = require('point_of_sale.BaseWidget');

    var _t      = core._t;
    var round_pr = utils.round_precision;


    var orderline_super = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({
        set_quantity: function (quantity, no_decrease) {
            var current_quantity = this.get_quantity();
            var future_quantity = parseFloat(quantity) || 0;
            if (no_decrease && (future_quantity === 0 || future_quantity < current_quantity)) {
                this.pos.gui.show_popup("number", {
                    'title': _t("Decrease the quantity by"),
                    'confirm': function (qty_decrease) {
                        if (qty_decrease) {
                            var order = this.pos.get_order();
                            var selected_orderline = order.get_selected_orderline();
                            qty_decrease = parseInt(qty_decrease, 10);

                             // We have to prevent taking back more than what was on the order. The
                            // right way to do this is by "merging" all the orderlines that we can
                            // with this one (including previous decreases). Then we can figure out
                            // how much the POS user can still decrease by.
                            var current_total_quantity_remaining = selected_orderline.get_quantity();
                            order.get_orderlines().forEach(function (orderline, index, array) {
                                if (selected_orderline.id != orderline.id &&
                                    selected_orderline.get_product().id === orderline.get_product().id &&
                                    selected_orderline.get_discount() === orderline.get_discount()) {
                                    current_total_quantity_remaining += orderline.get_quantity();
                                }
                            });

                             if (qty_decrease > current_total_quantity_remaining) {
                                this.pos.gui.show_popup("error", {
                                    'title': _t("Order error"),
                                    'body':  _t("Not allowed to take back more than was ordered."),
                                });
                            } else {
                                var decrease_line = order.get_selected_orderline().clone();
                                decrease_line.order = order;
                                decrease_line.set_quantity(-qty_decrease);
                                order.add_orderline(decrease_line);
                            }
                        }
                    }
                });
            } else {
                orderline_super.set_quantity.apply(this, arguments);
            }
        },
        can_be_merged_with: function(orderline) {
            var order = this.pos.get_order();
            var last_id = Object.keys(order.orderlines._byId)[Object.keys(order.orderlines._byId).length-1]

            if(order.orderlines._byId[last_id].product.id !== orderline.product.id || order.orderlines._byId[last_id].quantity < 0) {
                return false;
            } else {
                return orderline_super.can_be_merged_with.apply(this, arguments);
            }
        }
    });

     screens.OrderWidget.include({
        set_value: function (val) {
            var order = this.pos.get_order();
            var mode = this.numpad_state.get('mode');

             if (order.get_selected_orderline() && mode === 'quantity') {
                order.get_selected_orderline().set_quantity(val, "dont_allow_decreases");
            } else {
                this._super(val);
            }
        },

         update_summary: function () {
            if (this.pos.get_order()) {
                return this._super();
            } else {
                return undefined;
            }
        },

         orderline_change: function(line) {
            // don't try to rerender non-visible lines
            if (this.pos.get_order() && line.node && line.node.parentNode) {
                return this._super(line);
            } else {
                return undefined;
            }
        }
    });

    var ProductScreenWidget = screens.ScreenWidget.extend({
        _onKeypadKeyDown: function (ev) {
            console.log('tututu');
        },
    });
 });