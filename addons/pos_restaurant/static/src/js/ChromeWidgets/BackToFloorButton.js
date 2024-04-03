odoo.define('pos_restaurant.BackToFloorButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    /**
     * Props: {
     *     onClick: callback
     * }
     */
    class BackToFloorButton extends PosComponent {
        get table() {
            return this.env.pos.table;
        }
        get floor() {
            return this.table ? this.table.floor : null;
        }
        get hasTable() {
            return this.table != null;
        }
        backToFloorScreen() {
            if (this.props.onClick) {
                this.props.onClick();
            }
            this.showScreen('FloorScreen', { floor: this.floor });
        }
    }
    BackToFloorButton.template = 'BackToFloorButton';

    Registries.Component.add(BackToFloorButton);

    return BackToFloorButton;
});
