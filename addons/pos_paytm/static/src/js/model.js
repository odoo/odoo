odoo.define('pos_paytm.models', function (require) {
var models = require('point_of_sale.models');
var PaymentPaytm = require('pos_paytm.payment');

models.register_payment_method('paytm', PaymentPaytm);
});
