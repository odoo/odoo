odoo.define('point_of_sale.PaymentScreenNumpad', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const { PSNumpadInputButton } = require('point_of_sale.PSNumpadInputButton');

    class PaymentScreenNumpad extends PosComponent {}

    PaymentScreenNumpad.components = { PSNumpadInputButton };

    return { PaymentScreenNumpad };
});
