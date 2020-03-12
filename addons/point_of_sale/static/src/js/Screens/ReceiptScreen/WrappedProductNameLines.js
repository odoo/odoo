odoo.define('point_of_sale.WrappedProductNameLines', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const Registry = require('point_of_sale.ComponentsRegistry');

    class WrappedProductNameLines extends PosComponent {
        static template = 'WrappedProductNameLines';
        constructor() {
            super(...arguments);
            this.line = this.props.line;
        }
    }

    Registry.add('WrappedProductNameLines', WrappedProductNameLines);

    return { WrappedProductNameLines };
});
