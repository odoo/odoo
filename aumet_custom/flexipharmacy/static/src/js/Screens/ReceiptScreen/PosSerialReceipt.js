odoo.define('pos_serial.PosSerialReceipt', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class PosSerialReceipt extends PosComponent {}

    PosSerialReceipt.template = 'PosSerialReceipt';

    Registries.Component.add(PosSerialReceipt);

    return PosSerialReceipt;
});
