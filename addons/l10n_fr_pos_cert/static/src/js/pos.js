odoo.define('l10n_fr_pos_cert.pos', function (require) {
"use strict";

var models = require('point_of_sale.models');
var screens = require('point_of_sale.screens');
var rpc = require('web.rpc');
var session = require('web.session');
var core = require('web.core');
var utils = require('web.utils');

var _t = core._t;
var round_di = utils.round_decimals;

var _super_posmodel = models.PosModel.prototype;
models.PosModel = models.PosModel.extend({
    is_french_country: function(){
      var french_countries = ['FR', 'MF', 'MQ', 'NC', 'PF', 'RE', 'GF', 'GP', 'TF'];
      if (!this.company.country) {
        this.gui.show_popup("error", {
            'title': _t("Missing Country"),
            'body':  _.str.sprintf(_t('The company %s doesn\'t have a country set.'), this.company.name),
        });
        return false;
      }
      return _.contains(french_countries, this.company.country.code);
    },
    delete_current_order: function () {
        if (this.is_french_country() && this.get_order().get_orderlines().length) {
            this.gui.show_popup("error", {
                'title': _t("Fiscal Data Module error"),
                'body':  _t("Deleting of orders is not allowed."),
            });
        } else {
            _super_posmodel.delete_current_order.apply(this, arguments);
        }
    },
});


var _super_order = models.Order.prototype;
models.Order = models.Order.extend({
    initialize: function() {
        _super_order.initialize.apply(this,arguments);
        this.l10n_fr_hash = this.l10n_fr_hash || false;
        this.save_to_db();
    },
    export_for_printing: function() {
      var result = _super_order.export_for_printing.apply(this,arguments);
      result.l10n_fr_hash = this.get_l10n_fr_hash();
      return result;
    },
    set_l10n_fr_hash: function (l10n_fr_hash){
      this.l10n_fr_hash = l10n_fr_hash;
    },
    get_l10n_fr_hash: function() {
      return this.l10n_fr_hash;
    },
    wait_for_push_order: function() {
      var result = _super_order.wait_for_push_order.apply(this,arguments);
      result = Boolean(result || this.pos.is_french_country());
      return result;
    }
});

var orderline_super = models.Orderline.prototype;
models.Orderline = models.Orderline.extend({
    isLastLine: function() {
        var order = this.pos.get_order();
        var last_id = Object.keys(order.orderlines._byId)[Object.keys(order.orderlines._byId).length-1];
        var selectedLine = order? order.selected_orderline: null;

        return last_id === selectedLine.cid;
    },
    set_quantity: function (quantity, keep_price) {
        var current_quantity = this.get_quantity();
        var new_quantity = parseFloat(quantity) || 0;
        if (this.pos.is_french_country() && new_quantity < current_quantity && !this.reward_id && !(new_quantity === 0 && current_quantity === 1 && this.isLastLine())) {
            var quantity_to_decrease = current_quantity - new_quantity;
            this.pos.gui.show_popup("number", {
                'title': _t("Decrease the quantity by"),
                'confirm': function (qty_decrease) {
                    if (qty_decrease) {
                        var order = this.pos.get_order();
                        var selected_orderline = order.get_selected_orderline();
                        qty_decrease = qty_decrease.replace(_t.database.parameters.decimal_point, '.');
                        qty_decrease = parseFloat(qty_decrease);
                        var decimals = this.pos.dp['Product Unit of Measure'];
                        qty_decrease = round_di(qty_decrease, decimals);

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
                            var decrease_line = selected_orderline.clone();
                            decrease_line.order = order;
                            orderline_super.set_quantity.apply(decrease_line, [-qty_decrease, true]);
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
            var last_id = Object.keys(order.orderlines._byId)[Object.keys(order.orderlines._byId).length-1];

            if(this.pos.is_french_country() && (order.orderlines._byId[last_id].product.id !== orderline.product.id || order.orderlines._byId[last_id].quantity < 0)) {
                return false;
            } else {
                return orderline_super.can_be_merged_with.apply(this, arguments);
            }
        }
});


screens.PaymentScreenWidget.include({
    post_push_order_resolve: function (order, server_ids) {
        if (this.pos.is_french_country()) {
            var _super = this._super;
            var args = arguments;
            var self = this;
            var get_hash_prom = new Promise (function (resolve, reject) {
                rpc.query({
                        model: 'pos.order',
                        method: 'search_read',
                        domain: [['id', 'in', server_ids]],
                        fields: ['l10n_fr_hash'],
                        context: session.user_context,
                    }).then(function (result) {
                        order.set_l10n_fr_hash(result[0].l10n_fr_hash || false);
                    }).finally(function () {
                        _super.apply(self, args).then(function () {
                            resolve();
                        }).catch(function (error) {
                            reject(error);
                        });
                    });
            });
            return get_hash_prom;
        }
        else {
            return this._super(order, server_ids);
        }
    },
});

screens.ProductScreenWidget.include({
    _onKeypadKeyDown: function (event) {
        if (this.pos.is_french_country()) {
            var order = this.pos.get_order();
            var orderline = this.pos.get_order().selected_orderline;
            var last_id = Object.keys(order.orderlines._byId)[Object.keys(order.orderlines._byId).length-1];

             if( !orderline || (last_id === orderline.cid && orderline.quantity >= 0)){
                this._super(event);
            }
        } else {
            this._super(event);
        }
        },
   });

screens.NumpadWidget.include({
    start: function(event) {
        this._super(event);
        if (this.pos.is_french_country()) {
            this.$el.find('.numpad-minus').prop("disabled",true);
        }
    },
    clickChangeMode: function (event) {
        if (this.pos.is_french_country() && event.currentTarget.attributes['data-mode'].nodeValue === "price") {
            this.gui.show_popup("error", {
               'title': _t("Module error"),
               'body':  _t("Adjusting the price is not allowed."),
            });
        } else {
           this._super(event);
        }
    },
    clickAppendNewChar: function(event) {
        if (this.pos.is_french_country()) {
            var order = this.pos.get_order();
            var orderline = this.pos.get_order().selected_orderline;
            var last_id = Object.keys(order.orderlines._byId)[Object.keys(order.orderlines._byId).length-1];

            if(last_id === orderline.cid && orderline.quantity >= 0){
                this._super(event);
            }
        } else {
            this._super(event);
        }
    },
});



});
