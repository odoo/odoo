odoo.define('flexipharmacy.PurchaseHistoryReceipt', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class PurchaseHistoryReceipt extends PosComponent {}
    PurchaseHistoryReceipt.template = 'PurchaseHistoryReceipt';

    Registries.Component.add(PurchaseHistoryReceipt);

    return PurchaseHistoryReceipt;
});
