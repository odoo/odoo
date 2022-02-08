odoo.define('point_of_sale.CurrencyAmount', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class CurrencyAmount extends PosComponent {}
    CurrencyAmount.template = 'CurrencyAmount';

    Registries.Component.add(CurrencyAmount);

    return CurrencyAmount;
});
