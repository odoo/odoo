import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { OrderQrTicket } from "@pos_self_order/overrides/components/order_qr_ticket/order_qr_ticket";

patch(PosStore.prototype, {
    async initServerData() {
        const process = await super.initServerData(...arguments);
        this.data.connectWebSocket(
            "SEND_ORDER_IN_PREPARATION",
            this.orderUpdateFromSelfOrdering.bind(this)
        );
        return process;
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
    async orderUpdateFromSelfOrdering(data) {
        for (const order_id of data.order_ids) {
            const order = this.models["pos.order"].get(order_id);
            if (order) {
                await this.sendOrderInPreparation(order);
            }
        }
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
    async printOrderQrTicket() {
        const order = this.getOrder();
        await Promise.all([
            this.syncAllOrders({ orders: [order] }),
            this.printer.print(OrderQrTicket, { order }, this.printOptions),
        ]);
    },
});
