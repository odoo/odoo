import { ProductCatalogOrderLine } from "@product/product_catalog/order_line/order_line";
import { patch } from "@web/core/utils/patch";

patch(ProductCatalogOrderLine.prototype, {
    get showPrice() {
        return super.showPrice && !["mrp.production", "mrp.workorder"].includes(this.env.orderResModel);
    }
});
