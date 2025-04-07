import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async getServerOrders() {
        if (!this.session._self_ordering) {
            return;
        }
        return await this.data.searchRead("pos.order", [
            ["company_id", "=", this.config.company_id.id],
            ["state", "=", "draft"],
            "|",
            ["pos_reference", "ilike", "Kiosk"],
            ["pos_reference", "ilike", "Self-Order"],
            ["table_id", "=", false],
        ]);
    },
});
