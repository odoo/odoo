import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { patch } from "@web/core/utils/patch";

patch(OrderSummary.prototype, {
    async updateSelectedOrderline({ buffer, key }) {
        const res = await super.updateSelectedOrderline(...arguments);
        const selectedLine = this.pos.getOrder().getSelectedOrderline();
        if (selectedLine?.isDiscountLine) {
            if (["", null].includes(buffer) && key === "Backspace") {
                this._setValue("remove");
            } else {
                this.numberBuffer.reset();
            }
        }
        return res;
    },
});
