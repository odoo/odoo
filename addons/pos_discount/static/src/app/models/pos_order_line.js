import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    /**
     * Checks if the current line applies for a global discount from `pos_discount.DiscountButton`.
     * All lines are eligible for global discount except the discount product line itself.
     * @returns Boolean
     */
    isGlobalDiscountApplicable() {
        if (!this.config.tip_product_id?.id) {
            return true;
        }
        if (!this.product_id?.id) {
            return false;
        }
        return this.product_id.id !== this.config.tip_product_id.id;
    },
});
