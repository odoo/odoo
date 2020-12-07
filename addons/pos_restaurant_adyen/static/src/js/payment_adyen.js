odoo.define('pos_restaurant_adyen.payment', function (require) {
    "use strict";

    var PaymentAdyen = require('pos_adyen.payment');

    PaymentAdyen.include({
        _adyen_pay_data: function () {
            var data = this._super(...arguments);

            if (data.SaleToPOIRequest.PaymentRequest.SaleData.SaleToAcquirerData) {
                data.SaleToPOIRequest.PaymentRequest.SaleData.SaleToAcquirerData += "&authorisationType=PreAuth";
            } else {
                data.SaleToPOIRequest.PaymentRequest.SaleData.SaleToAcquirerData = "authorisationType=PreAuth";
            }

            return data;
        },

        send_payment_adjust: function (paymentId) {
            const payment = this.model.getRecord('pos.payment', paymentId);
            var data = {
                originalReference: payment.transaction_id,
                modificationAmount: {
                    value: parseInt(payment.amount * Math.pow(10, this.model.currency.decimal_places)),
                    currency: this.model.currency.name,
                },
                merchantAccount: this.payment_method.adyen_merchant_account,
                additionalData: {
                    industryUsage: 'DelayedCharge',
                },
            };

            return this._call_adyen(payment, data, 'adjust');
        },

        canBeAdjusted: function (paymentId) {
            const payment = this.model.getRecord('pos.payment', paymentId);
            return ['mc', 'visa', 'amex', 'discover'].includes(payment.card_type);
        }
    });
});
