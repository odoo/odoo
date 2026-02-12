import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { changesToOrder } from "@point_of_sale/app/models/utils/order_change";

patch(PosStore.prototype, {
    setOrder(order) {
        super.setOrder(order);
        if (
            order &&
            ((order.source === "kiosk" && !order.online_payment_method_id) ||
                (order.source === "mobile" && !order.use_self_order_online_payment)) &&
            !Object.keys(order.last_order_preparation_change.lines).length
        ) {
            const orderChange = changesToOrder(order, this.config.printerCategories, false);
            order.uiState.lastPrints.push(orderChange);
            order.updateLastOrderChange();
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
