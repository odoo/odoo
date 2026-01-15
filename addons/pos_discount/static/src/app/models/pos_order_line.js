import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    /**
     * Checks if the current line applies for a global discount from `pos_discount.DiscountButton`.
     * @returns Boolean
     */
    isGlobalDiscountApplicable() {
        return !(
            // Ignore existing discount line as not removing it before adding new discount line successfully
            (
                (this.config.tip_product_id &&
                    this.product_id.id === this.config.tip_product_id?.id) ||
                (this.config.discount_product_id &&
                    this.product_id.id === this.config.discount_product_id?.id)
            )
        );
    },
    get isDiscountLine() {
        return (
            this.config.module_pos_discount &&
            this.product_id.id === this.config.discount_product_id?.id
        );
    },
});
