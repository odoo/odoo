import { t, useProps } from "@odoo/owl";
import { ProductCatalogOrderLine } from "@product/product_catalog/order_line/order_line";

export class ProductCatalogPurchaseOrderLine extends ProductCatalogOrderLine {
    purchaseOrderLineProps = useProps({
        min_qty: t.number().optional(),
        packaging: t.object().optional(),
    });
}
