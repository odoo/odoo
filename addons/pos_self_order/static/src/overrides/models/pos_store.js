import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.onNotified("SELF_ORDERS_PAID", async ({ orders }) => {
            for (const { id, state } of orders) {
                const localOrder = this.models["pos.order"].get(id);
                if (localOrder && localOrder.state === "draft") {
                    localOrder.update({ state });
                }
            }
        });
    },
    async getServerOrders() {
        if (this.session._self_ordering) {
            await this.loadServerOrders([
                ["company_id", "=", this.config.company_id.id],
                ["state", "=", "draft"],
                "|",
                ["pos_reference", "ilike", "Kiosk"],
                ["pos_reference", "ilike", "Self-Order"],
                ["table_id", "=", false],
            ]);
        }

        return await super.getServerOrders(...arguments);
    },
    _shouldLoadOrders() {
        return super._shouldLoadOrders() || this.session._self_ordering;
    },
});

patch(PosOrder.prototype, {
    setup() {
        super.setup(...arguments);
        if (
            this.pos_reference?.startsWith("Self-Order") ||
            this.pos_reference?.startsWith("Kiosk")
        ) {
            this.tracking_number = "S" + this.tracking_number;
        }
    },
});
