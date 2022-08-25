odoo.define('point_of_sale.WrappedProductNameLines', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class WrappedProductNameLines extends PosComponent {}
    WrappedProductNameLines.template = 'WrappedProductNameLines';

    Registries.Component.add(WrappedProductNameLines);

    return WrappedProductNameLines;
});
