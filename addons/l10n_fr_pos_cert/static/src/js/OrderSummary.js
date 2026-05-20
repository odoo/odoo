import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { patch } from "@web/core/utils/patch";

patch(OrderSummary.prototype, {
    showOldUnitPrice(line) {
        return (
            this.pos.is_french_country() &&
            line.price_type === "manual" &&
            (!this.pos.config.module_pos_discount ||
                line.product_id.id !== this.pos.config.discount_product_id.id) &&
            !line.isTipLine() &&
            !line.is_reward_line
        );
    },
});
