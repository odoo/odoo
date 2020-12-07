odoo.define('l10n_co_pos.PointOfSaleModel', function (require) {
    'use strict';

    const PointOfSaleModel = require('point_of_sale.PointOfSaleModel');
    const session = require('web.session');
    const { patch } = require('web.utils');

    patch(PointOfSaleModel.prototype, 'l10n_co_pos', {
        async _postPushOrder(order) {
            await this._super(...arguments);
            if (this.country.code === 'CO') {
                const result = await this._rpc({
                    model: 'pos.order',
                    method: 'search_read',
                    domain: [['id', 'in', [order._extras.server_id]]],
                    fields: ['name'],
                    context: session.user_context,
                });
                order._extras.l10n_co_dian = result.length ? result[0].name : false;
            }
        },
        getOrderInfo(order) {
            const result = this._super(...arguments);
            result.l10n_co_dian = order._extras.l10n_co_dian;
            return result;
        },
    });

    return PointOfSaleModel;
});
