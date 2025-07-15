import { PosStore } from "@point_of_sale/app/services/pos_store";
import { TableQrTicket } from "@pos_self_order/overrides/screens/product_screen/table_qr_ticket/table_qr_ticket";
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
    async printTableQr() {
        const order = this.getOrder();
        order.is_dynamic_qr_order = true;
        this.addPendingOrder([order.id]);
        this.syncAllOrders({ orders: [order] });
        await this.printer.print(TableQrTicket, { order }, this.printOptions);
    },
    async _onBeforeDeleteOrder(order) {
        this.addPendingOrder([order.id], true);
        return await super._onBeforeDeleteOrder(order);
    },
});
