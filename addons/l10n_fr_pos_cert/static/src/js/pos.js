odoo.define('l10n_fr_pos_cert.pos', function (require) {
"use strict";

var models = require('point_of_sale.models');
var screens = require('point_of_sale.screens');
var rpc = require('web.rpc');
var session = require('web.session');

models.PosModel = models.PosModel.extend({
    is_french_country: function(){
      var french_countries = ['FR', 'MF', 'MQ', 'NC', 'PF', 'RE', 'GF', 'GP', 'TF'];
      return _.contains(french_countries, this.company.country.code);
    }
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
            return this._super(arguments);
        }
    },
});
});
