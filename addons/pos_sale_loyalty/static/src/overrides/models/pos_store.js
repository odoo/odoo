import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    async updatePrograms() {
        if (this.get_order().uiState._isSettlingSO) {
            return;
        }
        return super.updatePrograms();
    },

    updateRewards() {
        if (this.get_order().uiState._isSettlingSO) {
            return;
        }
        return super.updateRewards();
    },

    async settleSO(sale_order, orderFiscalPos) {
        await super.settleSO(sale_order, orderFiscalPos);
        // Re-apply loyalty once, since it was suppressed during settle.
        await this.updatePrograms();
        this.updateRewards();
    },
});
