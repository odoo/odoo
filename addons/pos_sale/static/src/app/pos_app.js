import { patch } from "@web/core/utils/patch";
import { Chrome } from "@point_of_sale/app/pos_app";

patch(Chrome.prototype, {
    sendOrderToCustomerDisplay(pos, routerState) {
        if (pos.selectedOrder?._isSettlingSO) {
            return;
        }
        return super.sendOrderToCustomerDisplay(pos, routerState);
    },
});
