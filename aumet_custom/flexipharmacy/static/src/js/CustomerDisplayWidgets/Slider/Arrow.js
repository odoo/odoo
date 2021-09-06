odoo.define('flexipharmacy.Arrow', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class Arrow extends PosComponent {
        get direction(){
            return this.props.direction === 'right' ? `right: 0px` : `left: 0px`;
        }
    }
    Arrow.template = 'Arrow';

    Registries.Component.add(Arrow);

    return Arrow;
});
