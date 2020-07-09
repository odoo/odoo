odoo.define('pos_restaurant.ReceiptScreen', function(require) {
    'use strict';

    const ReceiptScreen = require('point_of_sale.ReceiptScreen');
    const Registries = require('point_of_sale.Registries');

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
            /**
             * If this order is synced to/from the server, then the draft needs to be deleted
             * after the order is paid and the receipt screen is exited via 'Next Order' button.
             * Thus, we set this order to be removed from server. Note that only the draft version
             * is deleted if we trace the algorithm.
             */
            orderDone() {
                if (this.env.pos.config.iface_floorplan) {
                    this.env.pos.db.set_order_to_remove_from_server(this.currentOrder);
                }
                super.orderDone();
            }
        };

    Registries.Component.extend(ReceiptScreen, PosResReceiptScreen);

    return ReceiptScreen;
});
