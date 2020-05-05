odoo.define('pos_restaurant.BackToFloorButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');

    class BackToFloorButton extends PosComponent {
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
    BackToFloorButton.template = 'BackToFloorButton';

    Registries.Component.add(BackToFloorButton);

    return BackToFloorButton;
});
