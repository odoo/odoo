odoo.define('point_of_sale.PaymentMethodButton', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');

    class PaymentMethodButton extends PosComponent {
        static template = 'PaymentMethodButton';
    }

    return { PaymentMethodButton };
});
