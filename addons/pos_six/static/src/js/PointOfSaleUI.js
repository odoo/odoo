odoo.define('pos_six.PointOfSaleUI', function (require) {
    'use strict';

    const PointOfSaleUI = require('point_of_sale.PointOfSaleUI');
    const BalanceButton = require('pos_six.BalanceButton');
    const { patch } = require('web.utils');

    patch(PointOfSaleUI.prototype, 'pos_six', {
        get balanceButtonIsShown() {
            return this.env.model.data.derived.paymentMethods.some((pm) => pm.use_payment_terminal === 'six');
        },
    });

    patch(PointOfSaleUI, 'pos_six', {
        components: { ...PointOfSaleUI.components, BalanceButton },
    });

    return PointOfSaleUI;
});
