odoo.define('pos_restaurant.EditBar', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const { useState } = owl.hooks;

    class EditBar extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({ isColorPicker: false })
        }
    }
    EditBar.template = 'pos_restaurant.EditBar';

    return EditBar;
});
