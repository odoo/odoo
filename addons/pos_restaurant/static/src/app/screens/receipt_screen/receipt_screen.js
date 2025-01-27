import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";

patch(ReceiptScreen.prototype, {
    continueSplitting() {
        const originalOrderUuid = this.currentOrder.uiState.splittedOrderUuid;
        this.currentOrder.uiState.screen_data.value = "";
        this.currentOrder.uiState.locked = true;
        this.pos.selectedOrderUuid = originalOrderUuid;
        const nextOrderScreen = this.pos.getOrder().getCurrentScreenData().name;
        this.pos.showScreen(nextOrderScreen || "ProductScreen");
    },
    isContinueSplitting() {
        if (this.pos.config.module_pos_restaurant && !this.pos.selectedTable) {
            const splittedUuid = this.currentOrder.uiState.splittedOrderUuid;
            const splittedOrder = this.pos.models["pos.order"].getBy("uuid", splittedUuid);

            if (!splittedOrder) {
                return false;
            }

            return !splittedOrder.finalized;
        } else {
            return false;
        }
    },
});
