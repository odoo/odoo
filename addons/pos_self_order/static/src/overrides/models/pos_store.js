import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.selfOrderCount = 0;
        this.data.connectWebSocket("SELF_PAID_COUNT", (count) => {
            this.selfOrderCount = count;
        });
        if (this.config.self_ordering_mode === "mobile") {
            await this.updateSelfOrderCounts();
        }
    },
    async getServerOrders() {
        if (this.session._self_ordering) {
            await this.data.loadServerOrders([
                ["company_id", "=", this.config.company_id.id],
                ["state", "=", "draft"],
                ["source", "=", "kiosk"],
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
    async updateSelfOrderCounts() {
        await this.data.call("pos.config", "get_paid_self_order_count", [this.config.id], {});
    },
});
