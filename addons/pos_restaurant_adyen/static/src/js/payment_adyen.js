odoo.define('pos_restaurant_adyen.payment', function (require) {
    "use strict";

    var PaymentAdyen = require('pos_adyen.payment');
    var models = require('point_of_sale.models');

    PaymentAdyen.include({
        _adyen_pay_data: function () {
            var data = this._super();

            if (data.SaleToPOIRequest.PaymentRequest.SaleData.SaleToAcquirerData) {
                data.SaleToPOIRequest.PaymentRequest.SaleData.SaleToAcquirerData += "&authorisationType=PreAuth";
            } else {
                data.SaleToPOIRequest.PaymentRequest.SaleData.SaleToAcquirerData = "authorisationType=PreAuth";
            }
    
            return data;
        },

        send_payment_adjust: function (cid) {
            var order = this.pos.get_order();
            var line = order.get_paymentline(cid);
            var data = {
                originalReference: line.transaction_id,
                modificationAmount: {
                    value: parseInt(line.amount * Math.pow(10, this.pos.currency.decimals)),
                    currency: this.pos.currency.name,
                },
                merchantAccount: this.payment_method.adyen_merchant_account,
                additionalData: {
                    industryUsage: 'DelayedCharge',
                },
            };

            return this._call_adyen(data, 'adjust');
        },

        canBeAdjusted: function (cid) {
            var order = this.pos.get_order();
            var line = order.get_paymentline(cid);
            return ['mc', 'visa', 'amex', 'discover'].includes(line.card_type);
        }
    });
});
