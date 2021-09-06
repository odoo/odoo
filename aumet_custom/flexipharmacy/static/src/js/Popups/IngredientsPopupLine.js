odoo.define('flexipharmacy.IngredientsPopupLine', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class IngredientsPopupLine extends PosComponent {
        constructor() {
            super(...arguments);
        }
        async onClickLine(){
            this.props.line.isSelected = !this.props.line.isSelected;
        }
    }
    IngredientsPopupLine.template = 'IngredientsPopupLine';

    Registries.Component.add(IngredientsPopupLine);

    return IngredientsPopupLine;
});
