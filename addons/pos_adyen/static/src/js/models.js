odoo.define('pos_adyen.models', function (require) {
var models = require('point_of_sale.models');
var PaymentAdyen = require('pos_adyen.payment');

models.register_payment_method('adyen', PaymentAdyen);
models.load_fields('pos.payment.method', ['adyen_terminal_identifier', 'adyen_test_mode', 'adyen_api_key']);
});
