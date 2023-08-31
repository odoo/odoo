/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { OrderCart } from "@pos_self_order/kiosk/pages/order_cart/order_cart";

patch(OrderCart.prototype, {
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
