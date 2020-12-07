odoo.define('l10n_in_pos.PointOfSaleModel', function (require) {
    'use strict';

    const PointOfSaleModel = require('point_of_sale.PointOfSaleModel');
    const { patch } = require('web.utils');

    patch(PointOfSaleModel.prototype, 'l10n_in_pos', {
        _getOrderlineInfo(orderline) {
            const result = this._super(...arguments);
            const product = this.getRecord('product.product', orderline.product_id);
            result.l10n_in_hsn_code = product.l10n_in_hsn_code;
            return result;
        },
    });

    return PointOfSaleModel;
});
