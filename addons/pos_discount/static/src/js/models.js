/* @odoo-modules */

import { Orderline } from "@point_of_sale/js/models";
import { patch } from "@web/core/utils/patch";

patch(Orderline.prototype, "pos_discount.Orderline", {
    /**
     * Checks if the current line applies for a global discount from `pos_discount.DiscountButton`.
     * @returns Boolean
     */
    isGlobalDiscountApplicable() {
        const isTipsProduct =
            this.pos.config.tip_product_id && this.product.id === this.pos.config.tip_product_id[0];
        return !this.reward_id && !isTipsProduct;
    },
});
