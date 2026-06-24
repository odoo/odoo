import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    recomputeOrderData() {
        if (this.uiState._isSettlingSO) {
            return;
        }
        return super.recomputeOrderData();
    },
    //@override
    _getIgnoredProductIdsTotalDiscount() {
        const productIds = super._getIgnoredProductIdsTotalDiscount(...arguments);
        if (this.config.down_payment_product_id) {
            productIds.push(this.config.down_payment_product_id.id);
        }
        return productIds;
    },
});
