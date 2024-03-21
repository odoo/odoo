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
    continueSplitting() {
        const originalOrderUuid = this.currentOrder.uiState.splittedOrderUuid;
        this.currentOrder.uiState.screen_data.value = "";
        this.currentOrder.uiState.locked = true;
        this.pos.selectedOrderUuid = originalOrderUuid;
        this.pos.showScreen("ProductScreen");
    },
    isContinueSplitting() {
        if (this.pos.config.module_pos_restaurant && this.pos.selectedTable) {
            const originalOrderUuid = this.currentOrder.uiState.splittedOrderUuid;

            if (!originalOrderUuid) {
                return false;
            }

            return this.pos.models["pos.order"].find(
                (o) => o.uuid === originalOrderUuid && !o.finalized && o.lines.length
            );
        } else {
            return false;
        }
    },
    isResumeVisible() {
        if (this.isContinueSplitting()) {
            return false;
        }
        return super.isResumeVisible(...arguments);
    },
    //@override
    get nextScreen() {
        if (this.pos.config.module_pos_restaurant) {
            const table = this.pos.selectedTable;
            return { name: "FloorScreen", props: { floor: table ? table.floor_id : null } };
        } else {
            return super.nextScreen;
        }
    },
});
