odoo.define('pos_coupon.ActivePrograms', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    // TODO: Remove this component and put its contents to the OrderWidget template.
    class ActivePrograms extends PosComponent {}
    ActivePrograms.template = 'ActivePrograms';

    Registries.Component.add(ActivePrograms);

    return ActivePrograms;
});
