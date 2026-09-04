import { t, useProps } from "@odoo/owl";
import { ProductCatalogOrderLine } from "@product/product_catalog/order_line/order_line";

export class ProductCatalogAccountMoveLine extends ProductCatalogOrderLine {
    accountMoveLineProps = useProps({
        min_qty: t.number().optional(),
    });
}
