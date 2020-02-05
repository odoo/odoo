odoo.define('point_of_sale.Orderline', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');

    class Orderline extends PosComponent {
        constructor() {
            super(...arguments);
            this.line = this.props.line;
            this.pos = this.props.pos;
        }
        selectLine() {
            this.trigger('select-line', { orderline: this.line });
        }
        lotIconClicked() {
            this.trigger('show-product-lot', { orderline: this.line });
        }
    }

    return { Orderline };
});
