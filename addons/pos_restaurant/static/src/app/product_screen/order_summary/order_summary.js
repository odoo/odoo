/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";

patch(OrderSummary.prototype, {
    releaseTable() {
        const orderOnTable = this.pos.orders.filter(
            (o) => o.tableId === this.pos.selectedTable.id && o.finalized === false
        );
        for (const order of orderOnTable) {
            this.pos.removeOrder(order);
        }
        this.pos.showScreen("FloorScreen");
    },
    showReleaseBtn() {
        return (
            this.pos.config.module_pos_restaurant &&
            this.pos.selectedTable &&
            !this.pos.orders.some(
                (o) =>
                    o.tableId === this.pos.selectedTable.id &&
                    o.finalized === false &&
                    o.orderlines.length
            )
        );
    },
});
