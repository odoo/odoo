import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    updateRewards() {
        if (this.getOrder()?._isSettlingSO) {
            return;
        }
        return super.updateRewards();
    },

    async settleSO(sale_order, orderFiscalPos) {
        await super.settleSO(sale_order, orderFiscalPos);
        // Re-apply loyalty once, since it was suppressed during settle.
        this.updateRewards();
    },
});
