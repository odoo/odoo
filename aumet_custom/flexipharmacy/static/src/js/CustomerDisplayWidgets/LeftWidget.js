odoo.define('flexipharmacy.LeftWidget', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class LeftWidget extends PosComponent {}
    LeftWidget.template = 'LeftWidget';

    Registries.Component.add(LeftWidget);

    return LeftWidget;
});
