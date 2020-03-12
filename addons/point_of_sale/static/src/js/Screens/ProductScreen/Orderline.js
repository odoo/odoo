odoo.define('point_of_sale.Orderline', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const Registry = require('point_of_sale.ComponentsRegistry');

    class Orderline extends PosComponent {
        static template = 'Orderline';
        selectLine() {
            this.trigger('select-line', { orderline: this.props.line });
        }
        lotIconClicked() {
            this.trigger('edit-pack-lot-lines', { orderline: this.props.line });
        }
    }

    Registry.add('Orderline', Orderline);

    return { Orderline };
});
