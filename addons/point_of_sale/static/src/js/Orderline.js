odoo.define('point_of_sale.Orderline', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');

    class Orderline extends PosComponent {
        selectLine() {
            this.trigger('select-line', { orderline: this.props.line });
        }
        lotIconClicked() {
            this.trigger('show-product-lot', { orderline: this.props.line });
        }
    }

    return { Orderline };
});
