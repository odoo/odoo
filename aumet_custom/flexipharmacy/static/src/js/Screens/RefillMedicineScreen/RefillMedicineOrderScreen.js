odoo.define('point_of_sale.RefillMedicineOrderScreen', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    var rpc = require('web.rpc');

    class RefillMedicineOrderScreen extends PosComponent {}
    RefillMedicineOrderScreen.template = 'RefillMedicineOrderScreen';

    Registries.Component.add(RefillMedicineOrderScreen);

    return RefillMedicineOrderScreen;
});
