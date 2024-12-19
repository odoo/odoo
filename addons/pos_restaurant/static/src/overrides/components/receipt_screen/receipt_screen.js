import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";

patch(ReceiptScreen.prototype, {
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
        if (this.pos.config.module_pos_restaurant) {
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
    resumeOrder() {
        if (!this.pos.config.module_pos_restaurant) {
            return super.resumeOrder(...arguments);
        }
        this.currentOrder.uiState.screen_data.value = "";
        this.currentOrder.uiState.locked = true;
        this.pos.showScreen("TicketScreen", {
            stateOverride: {
                search: {
                    fieldName: "",
                    searchTerm: "",
                },
            },
        });
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
