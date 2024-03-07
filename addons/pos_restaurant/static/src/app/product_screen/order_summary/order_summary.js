/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";

patch(OrderSummary.prototype, {
    bookTable() {
        this.pos.get_order().setBooked(true);
        this.pos.showScreen("FloorScreen");
    },
    showBookButton() {
        return (
            this.pos.config.module_pos_restaurant &&
            this.pos.selectedTable &&
            !this.pos.orders.some(
                (o) =>
                    o.tableId === this.pos.selectedTable.id && o.finalized === false && o.isBooked
            )
        );
    },
    unbookTable() {
        this.pos.removeOrder(this.pos.get_order());
        this.pos.showScreen("FloorScreen");
    },
    showUnbookButton() {
        return (
            this.pos.config.module_pos_restaurant &&
            this.pos.selectedTable &&
            !this.pos.orders.some(
                (o) =>
                    o.tableId === this.pos.selectedTable.id && o.finalized === false && !o.isBooked
            ) &&
            this.pos.get_order().orderlines.length === 0
        );
    },
});
