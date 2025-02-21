import { ProductCatalogOrderLine } from "@product/product_catalog/order_line/order_line";

export class ProductCatalogSaleOrder extends ProductCatalogOrderLine {
    static props = {
        ...ProductCatalogOrderLine.props,
        last_invoice_date: { type: 'datetime', optional: true },
    }
}
