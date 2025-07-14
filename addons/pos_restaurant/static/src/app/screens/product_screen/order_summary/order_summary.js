import { patch } from "@web/core/utils/patch";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";

patch(OrderSummary.prototype, {
    bookTable() {
        this.pos.getOrder().setBooked(true);
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
        const order = this.pos.getOrder();
        await this.pos._onBeforeDeleteOrder(order);
        order.state = "cancel";
        this.pos.showScreen("FloorScreen");
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
                this.pos.getOrder().lines.length === 0
            );
        }
        const currentOrder = this.pos.getOrder();
        return (
            currentOrder &&
            this.pos.config.module_pos_restaurant &&
            !currentOrder.finalized &&
            currentOrder.isBooked &&
            currentOrder.lines.length === 0
        );
    },
    _setValue(val) {
        if (
            this.currentOrder.getSelectedOrderline() &&
            this.pos.numpadMode === "quantity" &&
            val === "remove" &&
            typeof this.currentOrder.id === "number"
        ) {
            this.pos.addPendingOrder([this.currentOrder.id]);
        }
        return super._setValue(val);
    },
});
