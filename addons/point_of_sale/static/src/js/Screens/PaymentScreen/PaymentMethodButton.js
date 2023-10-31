odoo.define('point_of_sale.PaymentMethodButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class PaymentMethodButton extends PosComponent {}
    PaymentMethodButton.template = 'PaymentMethodButton';

    Registries.Component.add(PaymentMethodButton);

    return PaymentMethodButton;
});
