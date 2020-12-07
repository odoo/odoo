odoo.define('pos_restaurant.Orderline', function (require) {
    'use strict';

    const Orderline = require('point_of_sale.Orderline');
    const { patch } = require('web.utils');

    patch(Orderline.prototype, 'pos_restaurant', {
        /**
         * @override
         * if doubleclick, change mp_dirty to mp_skip
         *
         * IMPROVEMENT: Instead of handling both double click and click in single
         * method, perhaps we can separate double click from single click.
         */
        onClickOrderline(orderline) {
            const order = this.env.model.getActiveOrder();
            const activeOrderline = this.env.model.getActiveOrderline(order);
            if (activeOrderline && activeOrderline.id !== orderline.id) {
                this.mp_dbclk_time = new Date().getTime();
            } else if (!this.mp_dbclk_time) {
                this.mp_dbclk_time = new Date().getTime();
            } else if (this.mp_dbclk_time + 500 > new Date().getTime()) {
                orderline.mp_skip = !orderline.mp_skip;
                this.mp_dbclk_time = 0;
            } else {
                this.mp_dbclk_time = new Date().getTime();
            }
            this._super(...arguments);
        },
    });

    return Orderline;
});
