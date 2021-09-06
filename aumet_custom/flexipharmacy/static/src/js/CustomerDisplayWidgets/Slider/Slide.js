odoo.define('flexipharmacy.Slide', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class Slide extends PosComponent {
        get content(){
            return this.props.content;
        }
    }
    Slide.template = 'Slide';

    Registries.Component.add(Slide);

    return Slide;
});
