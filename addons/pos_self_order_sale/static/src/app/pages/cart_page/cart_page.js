import { patch } from "@web/core/utils/patch";
import { CartPage } from "@pos_self_order/app/pages/cart_page/cart_page";
import { ProductCard } from "@pos_self_order/app/components/product_card/product_card";
import { onWillStart } from "@odoo/owl";

patch(CartPage.prototype, {
    setup() {
        super.setup(...arguments);
        onWillStart(() => {
            this.selfOrder.computeAvailableCategories();
        });
    },
    get optionalProducts() {
        const optionalProductIds = this.selfOrder.currentOrder.lines.flatMap(
            (line) => line.product_id.raw.optional_product_ids
        );

        const products = this.selfOrder.models["product.product"].filter(
            (p) => optionalProductIds.includes(p.raw.product_tmpl_id) && p.available_in_pos
        );

        return products;
    },
});
CartPage.components = { ...CartPage.components, ProductCard };
