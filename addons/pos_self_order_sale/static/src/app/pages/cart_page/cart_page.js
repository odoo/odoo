/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { CartPage } from "@pos_self_order/app/pages/cart_page/cart_page";
import { ProductCard } from "@pos_self_order/app/components/product_card/product_card";

patch(CartPage.prototype, {
    get optionalProducts() {
        const optionalProductIds = this.selfOrder.currentOrder.lines.flatMap(
            (line) => this.selfOrder.productByIds[line.product_id].optional_product_ids
        );
        // It can arrives that the optional product is not available in self.
        const products = this.selfOrder.products.filter((product) =>
            optionalProductIds.includes(product.id)
        );
        return products;
    },
});
CartPage.components = { ...CartPage.components, ProductCard };
