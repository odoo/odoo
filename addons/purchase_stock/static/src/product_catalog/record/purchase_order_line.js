import { t, useProps } from "@odoo/owl";
import { ProductCatalogPurchaseOrderLine } from "@purchase/product_catalog/purchase_order_line/purchase_order_line";

export class ProductCatalogPurchaseSuggestOrderLine extends ProductCatalogPurchaseOrderLine {
    purchaseSuggestOrderLineProps = useProps({
        suggested_qty: t.number().optional(),
    });
}
