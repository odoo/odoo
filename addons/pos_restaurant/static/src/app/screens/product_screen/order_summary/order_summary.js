import { patch } from "@web/core/utils/patch";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";

patch(OrderSummary.prototype, {
    bookTable() {
        this.pos.getOrder().setBooked(true);
        this.pos.navigate("FloorScreen");
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
    async onOrderlineLongPress(ev, orderline) {
        const result = await super.onOrderlineLongPress(ev, orderline);
        if (!result) {
            return false;
        }

        for (const child of orderline.combo_line_ids || []) {
            child.course_id = orderline.course_id;
        }

        return result;
    },
    async unbookTable() {
        const order = this.pos.getOrder();
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
                this.pos.getOrder().lines.length === 0 &&
                !this.pos.getOrder().hasCourses()
            );
        }
        const currentOrder = this.pos.getOrder();
        if (!currentOrder) {
            return false;
        }
        return (
            currentOrder &&
            this.pos.config.module_pos_restaurant &&
            !currentOrder.finalized &&
            currentOrder.isBooked &&
            currentOrder.isEmpty() &&
            !currentOrder.hasCourses()
        );
    },
    async updateSelectedOrderline({ buffer, key }) {
        await super.updateSelectedOrderline(...arguments);

        if (this.pos.getOrder() && this.pos.config.module_pos_restaurant) {
            this.pos.addPendingOrder([this.pos.getOrder().id]);
        }
    },
});
