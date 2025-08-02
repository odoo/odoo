import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async getServerOrders() {
        if (this.session._self_ordering) {
            const kioskOrderToFetch = this.data.models["pos.order"]
                .filter((order) => order.state == "draft" && order.pos_reference.includes("Kiosk"))
                .map((order) => order.id);

            await this.loadServerOrders([
                "|",
                "&",
                "&",
                ["company_id", "=", this.config.company_id.id],
                ["state", "=", "draft"],
                "&",
                "|",
                ["pos_reference", "ilike", "Kiosk"],
                ["pos_reference", "ilike", "Self-Order"],
                ["table_id", "=", false],
                ["id", "in", kioskOrderToFetch],
            ]);
        }

        return await super.getServerOrders(...arguments);
    },
});
