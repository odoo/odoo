odoo.define('pos_mercury.PosDialog', function (require) {
    'use strict';

    const PosDialog = require('point_of_sale.PosDialog');
    const PaymentTransactionPopup = require('pos_mercury.PaymentTransactionPopup');
    const { patch } = require('web.utils');

    patch(PosDialog, 'pos_mercury', {
        components: { ...PosDialog.components, PaymentTransactionPopup },
    });

    return PosDialog;
});
