import { ProductCatalogOrderLine } from "@product/product_catalog/order_line/order_line";

export class ProductCatalogPurchaseOrderLine extends ProductCatalogOrderLine {
    static props = {
        ...ProductCatalogPurchaseOrderLine.props,
        min_qty: { type: Number, optional: true },
        packaging: { type: Object, optional: true },
    };

    get highlightUoM() {
        return true;
    }
}
