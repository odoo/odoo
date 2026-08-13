import { patch } from "@web/core/utils/patch";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";

patch(OrderSummary.prototype, {
    bookTable() {
        this.pos.get_order().setBooked(true);
        this.pos.showScreen("FloorScreen");
    },
    showBookButton() {
        if (!this.pos.selectedTable) {
            return false;
        }
        return (
            this.pos.config.module_pos_restaurant &&
            !this.pos.models["pos.order"].some(
                (o) =>
                    o.table_id?.id === this.pos.selectedTable.id &&
                    o.finalized === false &&
                    o.isBooked
            )
        );
    },
    async unbookTable() {
        const order = this.pos.get_order();
        this.pos.showScreen(this.pos.firstScreen);
        order.state = "cancel";
        await this.pos.deleteOrders([order]);
    },
    showUnbookButton() {
        if (this.pos.selectedTable) {
            return (
                this.pos.config.module_pos_restaurant &&
                !this.pos.models["pos.order"].some(
                    (o) =>
                        o.table_id?.id === this.pos.selectedTable.id &&
                        o.finalized === false &&
                        !o.isBooked
                ) &&
                this.pos.get_order().lines.length === 0
            );
        }
        const currentOrder = this.pos.get_order();
        return (
            this.pos.config.module_pos_restaurant &&
            !currentOrder.finalized &&
            currentOrder.isBooked &&
            currentOrder.lines.length === 0
        );
    },
});
