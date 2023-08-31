/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { OrderCart } from "@pos_self_order/kiosk/pages/order_cart/order_cart";
import { ProductCard } from "@pos_self_order/kiosk/components/product_card/product_card";

patch(OrderCart.prototype, {
    get optionalProducts() {
        const optionalProductIds = this.selfOrder.currentOrder.lines.flatMap(
            (line) => this.selfOrder.productByIds[line.product_id]?.optional_product_ids || []
        );
        // It can arrives that the optional product is not available in self.
        const products = this.selfOrder.products.filter((product) =>
            optionalProductIds.includes(product.id)
        );

        return products;
    },
});
OrderCart.components = { ...OrderCart.components, ProductCard };
