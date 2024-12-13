import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";

patch(ReceiptScreen.prototype, {
    continueSplitting() {
        const originalOrderUuid = this.currentOrder.uiState.splittedOrderUuid;
        this.currentOrder.uiState.screen_data.value = "";
        this.currentOrder.uiState.locked = true;
        this.pos.selectedOrderUuid = originalOrderUuid;
        this.pos.showScreen("ProductScreen");
    },
    isContinueSplitting() {
        if (
            this.pos.config.module_pos_restaurant &&
            !this.pos.selectedTable &&
            !this.currentOrder.originalSplittedOrder
        ) {
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
});
