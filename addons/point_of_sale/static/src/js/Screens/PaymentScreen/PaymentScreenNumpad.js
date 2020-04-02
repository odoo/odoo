odoo.define('point_of_sale.PaymentScreenNumpad', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const { PSNumpadInputButton } = require('point_of_sale.PSNumpadInputButton');
    const Registry = require('point_of_sale.ComponentsRegistry');

    class PaymentScreenNumpad extends PosComponent {
        static template = 'PaymentScreenNumpad';
        constructor() {
            super(...arguments);
            this.decimalPoint = this.env._t.database.parameters.decimal_point;
        }
    }

    PaymentScreenNumpad.components = { PSNumpadInputButton };

    Registry.add('PaymentScreenNumpad', PaymentScreenNumpad);

    return { PaymentScreenNumpad };
});
