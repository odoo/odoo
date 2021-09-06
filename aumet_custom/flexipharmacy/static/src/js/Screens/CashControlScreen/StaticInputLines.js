odoo.define('flexipharmacy.StaticInputLines', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class StaticInputLines extends PosComponent {}
    StaticInputLines.template = 'StaticInputLines';

    Registries.Component.add(StaticInputLines);

    return StaticInputLines;
});

