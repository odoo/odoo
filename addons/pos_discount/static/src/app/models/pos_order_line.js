import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    /**
     * Checks if the current line applies for a global discount from `pos_discount.DiscountButton`.
     * @returns Boolean
     */
    isGlobalDiscountApplicable() {
<<<<<<< 157874aad3aebef5bc9268de6e17530641107e31
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
||||||| 14709d6b8b5a21b9bb75732ab9e12b6c8d32e08b
        return !(
            this.config.tip_product_id && this.product_id.id === this.config.tip_product_id?.id
        );
=======
        return this.isDiscountable();
>>>>>>> 4f541fb02f6cd92ae31df241728e3adcc79145b0
    },
});
