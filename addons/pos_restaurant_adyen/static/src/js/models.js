odoo.define('pos_restaurant_adyen.models', function (require) {
    var models = require('point_of_sale.models');

    models.load_fields('pos.payment.method', ['adyen_merchant_account']);
});
