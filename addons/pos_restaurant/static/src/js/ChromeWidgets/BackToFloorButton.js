odoo.define('pos_restaurant.BackToFloorButton', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const { useListener } = require('web.custom_hooks');
    const Registry = require('point_of_sale.ComponentsRegistry');

    class BackToFloorButton extends PosComponent {
        static template = 'BackToFloorButton';
        constructor() {
            super(...arguments);
            useListener('click', this._backToFloorScreen);
        }
        get table() {
            return this.props.table;
        }
        get floor() {
            return this.props.table.floor;
        }
        async _backToFloorScreen() {
            this.showScreen('FloorScreen', { floor: this.floor });
        }
    }

    Registry.add('BackToFloorButton', BackToFloorButton);

    return { BackToFloorButton };
});
