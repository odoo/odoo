/** @odoo-module **/
import { Product } from "@pos_self_order/common/models/product";
import { patch } from "@web/core/utils/patch";

patch(Product.prototype, {
    setup(product, showPriceTaxIncluded) {
        super.setup(...arguments);
        this.optional_product_ids = product.optional_product_ids || [];
    },
});
