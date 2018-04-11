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

var _super_order = models.Order;
models.Order = models.Order.extend({
    export_for_printing: function () {
        var json = _super_order.prototype.export_for_printing.apply(this, arguments);
        json.l10n_fr_hash = this.l10n_fr_hash;
        return json;
    },

    export_as_JSON: function () {
        var json = _super_order.prototype.export_as_JSON.apply(this, arguments);
        return _.extend(json, {
            'l10n_fr_hash': this.l10n_fr_hash,
            'l10n_fr_proforma': this.l10n_fr_proforma,
        });
    },

});

var _super_pos = models.PosModel.prototype;
models.PosModel = models.PosModel.extend({

    initialize: function(session, attributes) {
        this.certification_deferred = null;
        return _super_pos.initialize.call(this, session, attributes);
    },

    _save_to_server: function (orders, options) {
        this.certification_deferred = new $.Deferred();
        var order = this.get_order();
        var self = this;
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
                        self.certification_deferred.resolve(hash);
                        return server_ids;
                    }).fail(function (error, event) {
                        self.certification_deferred.reject();
                        return server_ids;
                    });
                }
                self.certification_deferred.resolve(false);
                return server_ids;
            }
            self.certification_deferred.reject();
        }, function error() {
           self.certification_deferred.reject();
        });
    },

    _l10n_fr_push_proforma: function () {
        var old_order = this.get_order();
        if (old_order && old_order.get_orderlines().length && old_order.l10n_fr_proforma !== false) {
            return this.push_order(old_order, undefined, true).then( function () {
                // mark the lines that have been pro forma'd, because we won't allow to change them
                old_order.get_orderlines().forEach(function (current, index, array) {
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


screens.ReceiptScreenWidget.include({
    // Overload Function
    show: function(){
        var self = this;
        var super_function = this._super;
        this.pos.certification_deferred.then(function success(hash) {
            super_function.apply(self);
        }, function error() {
            self.pos.get_order()._printed = true;
            super_function.apply(self);
            self.$('.pos-sale-ticket').hide();
            self.pos.gui.show_popup('confirm', {
                title: _t('Connection required'),
                body: _t('Can not print the bill because your point of sale is currently offline, do you want to retry?'),
                confirm: function () {
                    self.pos.get_order().finalized = false;
                    self.pos.get_order()._printed = false;
                    self.gui.show_screen('payment');
                },
                cancel: function() {
                    self.click_next();
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
        this._super();
    }
});

gui.define_screen({name:'receipt', widget: screens.ReceiptScreenWidget});

screens.ProductScreenWidget.include({
    start: function () {
        this._super();

        var reprint_button = this.action_buttons['reprint'];
        if (reprint_button) {
            var super_reprint_click = reprint_button.button_click;
            var self = this;
            reprint_button.button_click = function () {
                if (self.pos.old_receipt) {
                    self.pos.old_receipt = self.pos.old_receipt.replace(/(<div class="l10n_fr_hash">)(.*)(<\/div>)/, '$1DUPLICATA$3');
                }
                super_reprint_click.bind(self)();
            }
        }

        var print_bill_button = this.action_buttons['print_bill'];
        if (print_bill_button) {
            var super_print_bill_button_click = print_bill_button.button_click;
            print_bill_button.button_click = function () {
                var self = this;
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
                        super_print_bill_button_click.bind(self)();
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
        if (! order.l10n_fr_proforma) {
            this._super(order);
        }
    },
});

});
