odoo.define('pos_restaurant.EditBar', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { useState } = owl.hooks;

    class EditBar extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({ isColorPicker: false })
        }
    }
    EditBar.template = 'EditBar';

    Registries.Component.add(EditBar);

    return EditBar;
});
