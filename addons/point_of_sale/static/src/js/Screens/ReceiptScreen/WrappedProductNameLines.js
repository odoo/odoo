odoo.define('point_of_sale.WrappedProductNameLines', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');

    class WrappedProductNameLines extends PosComponent {
        constructor() {
            super(...arguments);
            this.line = this.props.line;
        }
    }

    return { WrappedProductNameLines };
});
