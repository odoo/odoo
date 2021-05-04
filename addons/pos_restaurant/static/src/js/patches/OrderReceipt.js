odoo.define('pos_restaurant.OrderReceipt', function (require) {
    'use strict';

    const OrderReceipt = require('point_of_sale.OrderReceipt');
    const { patch } = require('web.utils');

    patch(OrderReceipt.prototype, 'pos_restaurant', {
        _showRoundingInfo() {
            return this.props.isBill ? false : this._super(...arguments);
        },
    });

    return OrderReceipt;
});
