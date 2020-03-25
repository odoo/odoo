odoo.define('pos_restaurant.chrome', function(require) {
    'use strict';

    const { Chrome } = require('point_of_sale.chrome');
    const Registry = require('point_of_sale.ComponentsRegistry');

    const PosResChrome = Chrome =>
        class extends Chrome {
            /**
             * @override
             * Do not set `FloorScreen` to the order.
             */
            _setScreenData(name) {
                if (name === 'FloorScreen') return;
                super._setScreenData(...arguments);
            }
            /**
             * @override
             * `FloorScreen` is the start screen if there are floors.
             */
            get startScreen() {
                if (this.env.pos.config.iface_floorplan) {
                    const table = this.env.pos.table;
                    return { name: 'FloorScreen', props: { floor: table ? table.floor : null } };
                } else {
                    return super.startScreen;
                }
            }
            /**
             * @override
             * Order is set to null when table is selected. There is no saved
             * screen for null order so show `FloorScreen` instead.
             */
            _showSavedScreen(pos, newSelectedOrder) {
                if (!newSelectedOrder) {
                    this.showScreen('FloorScreen', { floor: pos.table.floor });
                } else {
                    super._showSavedScreen(pos, newSelectedOrder);
                }
            }
        };

    Registry.extend(Chrome.name, PosResChrome);
});
