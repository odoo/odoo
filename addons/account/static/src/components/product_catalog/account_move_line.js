import { ProductCatalogOrderLine } from "@product/product_catalog/order_line/order_line";

export class ProductCatalogAccountMoveLine extends ProductCatalogOrderLine {
    static props = {
        ...ProductCatalogOrderLine.props,
        min_qty: { type: Number, optional: true },
    };
}
