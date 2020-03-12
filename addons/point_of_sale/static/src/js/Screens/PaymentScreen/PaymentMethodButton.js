odoo.define('point_of_sale.PaymentMethodButton', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const Registry = require('point_of_sale.ComponentsRegistry');

    class PaymentMethodButton extends PosComponent {
        static template = 'PaymentMethodButton';
    }

    Registry.add('PaymentMethodButton', PaymentMethodButton);

    return { PaymentMethodButton };
});
