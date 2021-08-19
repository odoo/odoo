odoo.define('point_of_sale.RefillMedicineScreenLine', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class RefillMedicineScreenLine extends PosComponent {
        constructor() {
            super(...arguments);
        }
    }
    RefillMedicineScreenLine.template = 'RefillMedicineScreenLine';

    Registries.Component.add(RefillMedicineScreenLine);

    return RefillMedicineScreenLine;
});
