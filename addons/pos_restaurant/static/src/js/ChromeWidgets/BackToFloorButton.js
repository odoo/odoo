odoo.define('pos_restaurant.BackToFloorButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { posbus } = require('point_of_sale.utils');

    class BackToFloorButton extends PosComponent {
        mounted() {
            posbus.on('table-set', this, this.render);
        }
        willUnmount() {
            posbus.on('table-set', this);
        }
        get table() {
            return (this.env.pos && this.env.pos.table) || null;
        }
        get floor() {
            const table = this.table;
            return table ? table.floor : null;
        }
        get hasTable() {
            return this.table !== null;
        }
        backToFloorScreen() {
            this.showScreen('FloorScreen', { floor: this.floor });
        }
    }
    BackToFloorButton.template = 'BackToFloorButton';

    Registries.Component.add(BackToFloorButton);

    return BackToFloorButton;
});
