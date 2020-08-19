odoo.define('pos_restaurant_adyen.payment', function (require) {
    "use strict";

    var PaymentAdyen = require('pos_adyen.payment');
    var models = require('point_of_sale.models');

    PaymentAdyen.include({
        _adyen_pay_data: function () {
            var data = this._super();

            if (this.pos.config.set_tip_after_payment) {
                data.SaleToPOIRequest.PaymentRequest.SaleData.SaleToAcquirerData = "authorisationType=PreAuth";
            }
    
            return data;
        },
    });

    var paymentline_super = models.Paymentline.prototype;
    models.Paymentline = models.Paymentline.extend({
        canBeTipped: function () {
            if (this.payment_method.use_payment_terminal === 'adyen') {
                return ['mc', 'visa', 'amex', 'discover'].includes(this.card_type);
            }
            return paymentline_super.canBeTipped.apply(this);
        },
    });
});
