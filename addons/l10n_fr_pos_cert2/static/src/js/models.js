odoo.define('l10n_fr_pos_cert2.models', function (require) {
"use strict";

var models = require('point_of_sale.models');
var screens = require('point_of_sale.screens');
var gui = require('point_of_sale.gui');
var DB = require('point_of_sale.DB');
var Model = require('web.DataModel');
var core = require('web.core');
var QWeb = core.qweb;

var _t = core._t;


var certification_deferred = null;

var _super_order = models.Order;
models.Order = models.Order.extend({
    export_for_printing: function () {
        var json = _super_order.prototype.export_for_printing.apply(this, arguments);
        json.l10n_fr_hash = this.l10n_fr_hash;
        return json
    },

    export_as_JSON: function () {
        var json = _super_order.prototype.export_as_JSON.apply(this,arguments);
        return _.extend(json, {
            'l10n_fr_hash': this.l10n_fr_hash,
            'l10n_fr_proforma': this.l10n_fr_proforma,
        });
    },

});

//to add if we don't want modifications of existing lines
/*
var orderline_super = models.Orderline.prototype;
models.Orderline = models.Orderline.extend({
    init_from_JSON: function (json) {
        orderline_super.init_from_JSON.apply(this, arguments);
        this.l10n_fr_proforma_finalized = json.l10n_fr_proforma_finalized;
    },

    export_as_JSON: function () {
        var json = orderline_super.export_as_JSON.apply(this, arguments);

        return _.extend(json, {
            'l10n_fr_proforma_finalized': this.l10n_fr_proforma_finalized
        });
    },

    set_discount: function (discount) {
        if (this.l10n_fr_proforma_finalized) {
            this._show_finalized_error();
        } else {
            orderline_super.set_discount.apply(this, arguments);
        }
    },

    set_unit_price: function (price) {
        if (this.l10n_fr_proforma_finalized) {
            this._show_finalized_error();
        } else {
            orderline_super.set_unit_price.apply(this, arguments);
        }
    },

    set_quantity: function(quantity){
        if (this.l10n_fr_proforma_finalized) {
            this._show_finalized_error();
        } else {
            orderline_super.set_quantity.apply(this, arguments);
        }
    },

    _show_finalized_error: function () {
        this.pos.gui.show_popup("error", {
            'title': _t("Order error"),
            'body':  _t("This orderline has already been finalized in a pro forma order and " +
                "can no longer be modified. Please create a new line with eg. a negative quantity."),
        });
    },

    can_be_merged_with: function (orderline, ignore_blackbox_finalized) {
        if (this.l10n_fr_proforma_finalized || orderline.l10n_fr_proforma_finalized) {
            return false;
        } else {
            return orderline_super.can_be_merged_with.apply(this, arguments);
        }
    },
});
*/

var _super_pos = models.PosModel.prototype;
models.PosModel = models.PosModel.extend({
    _save_to_server: function (orders, options) {
        certification_deferred = new $.Deferred();
        var order = this.get('selectedOrder');
        return _super_pos._save_to_server.apply(this, arguments).then(function (server_ids) {
            if (server_ids) {
                if (server_ids.length > 0) {
                    // Try to get hash of saved orders, if required
                    var posOrderModel = new Model('pos.order');
                    return posOrderModel.call(
                        'get_l10n_fr_hash', [server_ids], false
                    ).then(function (results) {
                        var hash = false;
                        _.each(results, function (result) {
                            if (result.pos_reference.indexOf(order.uid) > 0) {
                                hash = result.l10n_fr_hash;
                                order.l10n_fr_hash = hash;
                            }
                        });
                        certification_deferred.resolve(hash);
                        return server_ids;
                    }).fail(function (error, event) {
                        certification_deferred.reject();
                        return server_ids;
                    });
                }
                certification_deferred.resolve(false);
                return server_ids;
            }
            certification_deferred.reject();
        }, function error() {
             certification_deferred.reject();
        });
    },

    _l10n_fr_push_proforma: function () {
        var old_order = this.get_order();
        if (old_order && old_order.get_orderlines().length && old_order.l10n_fr_proforma !== false) {
            return this.push_order(old_order, undefined, true).then( function () {
                // mark the lines that have been pro forma'd, because we won't allow to change them
                old_order.get_orderlines().forEach(function (current, index, array) {
                    current.l10n_fr_proforma_finalized = true;
                    current.trigger('change', current); // force export
                });
            });
        } else {
            return new $.Deferred().reject();
        }
    },

    push_order: function (order, opts, proforma) {

        if (order) {
            order.l10n_fr_proforma = proforma || false;

            return _super_pos.push_order.apply(this, [order, opts]);
        } else {
            return _super_pos.push_order.apply(this, arguments);
        }
    },
});

var ReceiptScreenWidgetParent = screens.ReceiptScreenWidget;
screens.ReceiptScreenWidget = screens.ReceiptScreenWidget.extend({
    // Overload Function
    show: function(){
        var self = this;
        certification_deferred.then(function success(hash) {
                ReceiptScreenWidgetParent.prototype.show.apply(self, []);
        }, function error() {
            self.pos.get('selectedOrder')._printed = true;
            ReceiptScreenWidgetParent.prototype.show.apply(self, []);
            self.$('.pos-sale-ticket').hide();
            self.pos.gui.show_popup('confirm', {
                title: _t('Connection required'),
                body: _t('Can not print the bill because your point of sale is currently offline, do you want to retry?'),
                confirm: function () {
                    self.pos.get('selectedOrder').finalized = false;
                    self.pos.get('selectedOrder')._printed = false;
                    self.gui.show_screen('payment');
                },
                cancel: function() {
                    self.click_next()
                }
            });
        });
    },
    print: function () {
        var env = {
            widget:  this,
            pos:     this.pos,
            order:   this.pos.get_order(),
            receipt: this.pos.get_order().export_for_printing(),
            paymentlines: this.pos.get_order().get_paymentlines()
        };
        var receipt = QWeb.render('XmlReceipt',env);
        var posOrderModel = new Model('pos.order');
        posOrderModel.call('save_ticket', [this.pos.get_order().export_as_JSON(), receipt, {}]);
        ReceiptScreenWidgetParent.prototype.print.apply(this, []);
    }
});

gui.define_screen({name:'receipt', widget: screens.ReceiptScreenWidget});

screens.ProductScreenWidget.include({
    start: function () {
        this._super();

        var reprint_button = this.action_buttons['reprint'];
        if (reprint_button) {
            var super_reprint_click = reprint_button.button_click;
            self = this;
            reprint_button.button_click = function () {
                if (self.pos.old_receipt) {
                    self.pos.old_receipt = self.pos.old_receipt.replace(/(<div class="l10n_fr_hash">)(.*)(<\/div>)/, '$1DUPLICATA$3');
                }
                super_reprint_click.bind(self)()
            }
        }

        var print_bill_button = this.action_buttons['print_bill'];
        if (print_bill_button) {
            var super_print_bill_button_click = print_bill_button.button_click;
            print_bill_button.button_click = function () {
                self = this;
                var order = self.pos.get_order();
                if(order.get_orderlines().length > 0){
                    self.pos._l10n_fr_push_proforma().then(function () {
                        var receipt = order.export_for_printing();
                        receipt.bill = true;
                        var html_receipt = QWeb.render('BillReceipt',{
                            receipt: receipt, widget: self, pos: self.pos, order: order,
                        });
                        var posOrderModel = new Model('pos.order');
                        posOrderModel.call('save_ticket', [self.pos.get_order().export_as_JSON(), html_receipt, {}]);
                        super_print_bill_button_click.bind(self)()
                    });
                }
            }
        }
    }
});

DB.include({
    // do not remove pro forma to keep them in localstorage after sent
    // to server and avoid losing it when the browser is closed
    remove_unpaid_order: function(order){
        var orders = this.load('unpaid_orders',[]);
        orders = _.filter(orders, function(o){
            return (order.l10n_fr_proforma === true ||
                    o.id !== order.uid);
        });
        this.save('unpaid_orders',orders);
    },
});

});
