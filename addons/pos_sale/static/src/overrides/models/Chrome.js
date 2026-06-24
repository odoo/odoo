import { patch } from "@web/core/utils/patch";
import { Chrome } from "@point_of_sale/app/pos_app";

patch(Chrome.prototype, {
    sendOrderToCustomerDisplay(selectedOrder, scaleData) {
        if (selectedOrder.uiState._isSettlingSO) {
            return;
        }
        return super.sendOrderToCustomerDisplay(selectedOrder, scaleData);
    },
});
