odoo.define('pos_adyen_tipping.payment', function (require) {
"use strict";

var core = require('web.core');
var rpc = require('web.rpc');
var PosAdyenPayment = require('pos_adyen.payment');
var models = require('point_of_sale.models');

PosAdyenPayment.include({
    _set_notification_data_on_line: function (line, additional_response) {
        this._super.apply(this, arguments);
        var order = line.order;
        order.card_name = additional_response.get('cardHolderName');
        order.trigger('change', order);
    },

    send_payment_request: function (cid) {
        var self = this;
        var self_super = this._super; // js is funny
        return this.cancel_last_authorization(this.pos.get_order()).then(function () {
            return self_super.apply(self, arguments);
        });
    },

    cancel_last_authorization: function (order) {
        if (!order.authorization_id) {
            return Promise.resolve();
        }

        var payment_method = order.authorization_payment_method;
        return rpc.query({
            model: 'pos.payment.method',
            method: 'cancel_authorization',
            args: [order.authorization_id,
                   payment_method.adyen_test_mode,
                   payment_method.adyen_api_key,
                   payment_method.adyen_merchant_account],
        }, {
            timeout: 5000
        }).then(function () {
            order.authorization_payment_method = false;
            order.authorization_id = false;
        }).catch(function (data) {
            self._show_error(_('Could not connect to the Odoo server, please check your internet connection and try again.'));
        });
    }
});

models.load_fields('pos.payment.method', 'adyen_merchant_account');

var _super_order = models.Order.prototype;
models.Order = models.Order.extend({
    export_as_JSON: function () {
        var json = _super_order.export_as_JSON.apply(this, arguments);
        json.card_name = this.card_name;
        return json;
    },
    init_from_JSON: function (json) {
        _super_order.init_from_JSON.apply(this, arguments);
        this.card_name = json.card_name || '';
    },
});
});
