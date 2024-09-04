import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async getServerOrders() {
        if (this.session._self_ordering) {
            await this.loadServerOrders([
                ["company_id", "=", this.config.company_id.id],
                ["state", "=", "draft"],
                "|",
                ["name", "ilike", "Kiosk"],
                ["name", "ilike", "Self-Order"],
                ["table_id", "=", false],
            ]);
        }

        return await super.getServerOrders(...arguments);
    },
    _shouldLoadOrders() {
        return super._shouldLoadOrders() || this.session._self_ordering;
    },
});
