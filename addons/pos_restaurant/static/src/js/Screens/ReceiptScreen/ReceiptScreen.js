odoo.define('pos_restaurant.ReceiptScreen', function(require) {
    'use strict';

    const { ReceiptScreen } = require('point_of_sale.ReceiptScreen');
    const Registry = require('point_of_sale.ComponentsRegistry');

    const PosResReceiptScreen = ReceiptScreen =>
        class extends ReceiptScreen {
            /**
             * @override
             */
            get nextScreen() {
                if (
                    this.env.pos.config.module_pos_restaurant &&
                    this.env.pos.config.iface_floorplan
                ) {
                    const table = this.env.pos.table;
                    return { name: 'FloorScreen', props: { floor: table ? table.floor : null } };
                } else {
                    return super.nextScreen;
                }
            }
        };

    Registry.extend(ReceiptScreen.name, PosResReceiptScreen);
});
