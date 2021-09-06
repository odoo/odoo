odoo.define('flexipharmacy.RightWidget', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { useRef } = owl.hooks;

    class RightWidget extends PosComponent {
        constructor() {
            super(...arguments);
            this.sliderRef = useRef('slider');
        }
    }
    RightWidget.template = 'RightWidget';

    Registries.Component.add(RightWidget);

    return RightWidget;
});
