odoo.define('pos_stripe.models', function (require) {
var models = require('point_of_sale.models');
var PaymentStripe = require('pos_stripe.payment');

models.register_payment_method('stripe', PaymentStripe);
});
