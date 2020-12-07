odoo.define('pos_restaurant.ReceiptScreen', function (require) {
    'use strict';

    const ReceiptScreen = require('point_of_sale.ReceiptScreen');
    const { patch } = require('web.utils');

    patch(ReceiptScreen.prototype, 'pos_restaurant', {
        get nextScreen() {
            if (this.env.model.ifaceFloorplan) {
                return 'FloorScreen';
            } else {
                return this._super();
            }
        },
    });

    return ReceiptScreen;
});
