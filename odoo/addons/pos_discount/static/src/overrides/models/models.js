/* @odoo-modules */

import { Orderline } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Orderline.prototype, {
    /**
     * Checks if the current line applies for a global discount from `pos_discount.DiscountButton`.
     * @returns Boolean
     */
    isGlobalDiscountApplicable() {
        return !(
            this.pos.config.tip_product_id && this.product.id === this.pos.config.tip_product_id[0]
        );
    },
});
