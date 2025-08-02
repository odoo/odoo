import { ProductCatalogPurchaseOrderLine } from "@purchase/product_catalog/purchase_order_line/purchase_order_line";

export class ProductCatalogPurchaseSuggestOrderLine extends ProductCatalogPurchaseOrderLine {
    static template = "purchase_stock.ProductCatalogPurchaseSuggestOrderLine";
    static props = {
        ...ProductCatalogPurchaseOrderLine.props,
        suggested_qty: { type: Number, optional: true },
    };
}
