import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
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
    setOrder(order) {
        super.setOrder(order);
        if (
            order &&
            ((order.pos_reference.includes("Kiosk") && !order.online_payment_method_id) ||
                (order.pos_reference.includes("Self-Order") &&
                    !order.use_self_order_online_payment)) &&
            this.getOrderChanges(order).nbrOfChanges
        ) {
            const orderChange = this.changesToOrder(order, this.config.printerCategories);
            order.uiState.lastPrint = orderChange;
            order.updateLastOrderChange();
        }
    },
});
