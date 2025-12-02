import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";

patch(ReceiptScreen.prototype, {
    continueSplitting() {
        const originalOrderUuid = this.currentOrder.uiState.splittedOrderUuid;
        this.currentOrder.uiState.screen_data.value = "";
        this.pos.selectedOrderUuid = originalOrderUuid;
        const nextOrderScreen = this.pos.getOrder().getCurrentScreenData().name;
        this.pos.navigate(nextOrderScreen || "ProductScreen", {
            orderUuid: originalOrderUuid,
        });
    },
    isContinueSplitting() {
        if (this.pos.config.module_pos_restaurant && !this.pos.selectedTable) {
            const splittedOrder = this.currentOrder.originalSplittedOrder;

            if (!splittedOrder) {
                return false;
            }

            return !splittedOrder.finalized;
        } else {
            return false;
        }
    },
});
