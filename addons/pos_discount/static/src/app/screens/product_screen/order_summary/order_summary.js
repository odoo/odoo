import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { patch } from "@web/core/utils/patch";

patch(OrderSummary.prototype, {
    async updateSelectedOrderline({ buffer, key }) {
        const selectedLine = this.pos.getOrder().getSelectedOrderline();
        if (!selectedLine?.isDiscountLine) {
            return super.updateSelectedOrderline(...arguments);
        }
        this.numberBuffer.reset();
        if (["Backspace", "Delete"].includes(key)) {
            if (this.currentOrder.isRefund) {
                return this.pos.showDiscountLineEditError();
            }
            this.currentOrder.removeOrderline(selectedLine);
            this.pos.numpadMode = "quantity";
        }
    },
});
