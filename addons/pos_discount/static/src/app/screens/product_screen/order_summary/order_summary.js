import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { patch } from "@web/core/utils/patch";

patch(OrderSummary.prototype, {
    _setValue(val) {
        if (
            this.pos.isDiscountLineSelected &&
            !isNaN(parseFloat(val)) &&
            this.currentOrder.getSelectedOrderline()?.price_unit < 0
        ) {
            const isNegativeKeyPressed = this.numberBuffer.eventsBuffer?.[0].detail?.key === "-";
            val = (isNegativeKeyPressed ? 1 : -1) * Math.abs(val);
            isNegativeKeyPressed && this.numberBuffer.set(val.toString());
        }
        super._setValue(val.toString());
    },
});
