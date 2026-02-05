import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async processServerData() {
        await super.processServerData(...arguments);
        if (["mobile", "kiosk"].includes(this.config.self_ordering_mode)) {
            this.models["pos.order"].addEventListener("create", async (data) => {
                // When "create" is called with empty orders, it means all the
                // synchronizations have settled, and we can update the record without
                // risking those updates being overridden by an ongoing synchronization.
                const safeToUpdate = data.ids.length === 0;
                if (safeToUpdate) {
                    this.models["pos.order"].forEach((order) => {
                        if (
                            ["kiosk", "mobile"].includes(order.source) &&
                            !order.online_payment_method_id &&
                            !Object.keys(order.last_order_preparation_change.lines).length
                        ) {
                            order.updateLastOrderChange();
                        }
                    });
                }
            });
        }
    },
    async getServerOrders() {
        if (this.session._self_ordering) {
            await this.data.loadServerOrders([
                ["company_id", "=", this.config.company_id.id],
                ["state", "=", "draft"],
                ["source", "in", ["kiosk", "mobile"]],
                ["self_ordering_table_id", "=", false],
            ]);
        }

        return await super.getServerOrders(...arguments);
    },
    async redirectToQrForm() {
        const user_data = await this.data.call("pos.config", "get_pos_qr_order_data", [
            this.config.id,
        ]);
        return await this.action.doAction({
            type: "ir.actions.client",
            tag: "pos_qr_stands",
            params: { data: user_data },
        });
    },
});
