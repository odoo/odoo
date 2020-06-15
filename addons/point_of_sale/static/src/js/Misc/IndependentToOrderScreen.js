odoo.define('point_of_sale.IndependentToOrderScreen', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');

    class IndependentToOrderScreen extends PosComponent {
        close() {
            // To close this order-indenpendent screen, we forcefully trigger change
            // on the selectedOrder attribute, which then shows the screen of the
            // current order.
            this.env.pos.trigger('change:selectedOrder', this.env.pos, this.env.pos.get_order(), {
                silent: true,
            });
        }
    }

    return IndependentToOrderScreen;
});
