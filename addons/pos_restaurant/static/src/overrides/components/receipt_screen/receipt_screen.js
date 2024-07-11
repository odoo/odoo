/** @odoo-module */

import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";
import { onWillUnmount } from "@odoo/owl";
import { FloorScreen } from "@pos_restaurant/app/floor_screen/floor_screen";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
        onWillUnmount(() => {
            // When leaving the receipt screen to the floor screen the order is paid and can be removed
            if (this.pos.mainScreen.component === FloorScreen && this.currentOrder.finalized) {
                this.pos.removeOrder(this.currentOrder);
            }
        });
    },
    //@override
    _addNewOrder() {
        if (!this.pos.config.module_pos_restaurant) {
            super._addNewOrder(...arguments);
        }
    },
    isResumeVisible() {
        if (this.pos.config.module_pos_restaurant && this.pos.table) {
            return this.pos.getTableOrders(this.pos.table.id).length > 1;
        }
        return super.isResumeVisible(...arguments);
    },
    //@override
    get nextScreen() {
        if (this.pos.config.module_pos_restaurant) {
            const table = this.pos.table;
            return { name: "FloorScreen", props: { floor: table ? table.floor : null } };
        } else {
            return super.nextScreen;
        }
    },
});
