/** @odoo-module */

import { ReceiptScreen } from "@point_of_sale/js/Screens/ReceiptScreen/ReceiptScreen";
import { usePos } from "@point_of_sale/app/pos_hook";
import { patch } from "@web/core/utils/patch";
import { onWillUnmount } from "@odoo/owl";
import { FloorScreen } from "@pos_restaurant/app/floor_screen/floor_screen";

patch(ReceiptScreen, "pos_restaurant.ReceiptScreen", {
    showBackToFloorButton: true,
});

patch(ReceiptScreen.prototype, "pos_restaurant.ReceiptScreen", {
    setup() {
        this._super(...arguments);
        this.pos = usePos();
        onWillUnmount(() => {
            // When leaving the receipt screen to the floor screen the order is paid and can be removed
            if (this.pos.mainScreen.component === FloorScreen && this.currentOrder.finalized) {
                this.env.pos.removeOrder(this.currentOrder);
            }
        });
    },
    //@override
    _addNewOrder() {
        if (!this.env.pos.config.iface_floorplan) {
            this._super(...arguments);
        }
    },
    isResumeVisible() {
        if (this.env.pos.config.iface_floorplan &&
            this.env.pos.table) {
                return this.env.pos.getTableOrders(this.env.pos.table.id).length > 1;
            }
        return this._super(...arguments);
    },
    //@override
    get nextScreen() {
        if (this.env.pos.config.iface_floorplan) {
            const table = this.env.pos.table;
            return { name: "FloorScreen", props: { floor: table ? table.floor : null } };
        } else {
            return this._super(...arguments);
        }
    },
});
