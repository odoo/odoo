odoo.define('point_of_sale.PaymentScreenNumpad', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { localization } = require('@web/core/l10n/localization');

    class PaymentScreenNumpad extends PosComponent {
        setup() {
            super.setup();
            this.decimalPoint = localization.decimalPoint;
        }
    }
    PaymentScreenNumpad.template = 'PaymentScreenNumpad';

    Registries.Component.add(PaymentScreenNumpad);

    return PaymentScreenNumpad;
});
