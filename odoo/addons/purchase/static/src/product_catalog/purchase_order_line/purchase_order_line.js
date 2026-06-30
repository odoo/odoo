/** @odoo-module */
import { ProductCatalogOrderLine } from "@product/product_catalog/order_line/order_line";

export class ProductCatalogPurchaseOrderLine extends ProductCatalogOrderLine {
    static template = "ProductCatalogPurchaseOrderLine";
    static props = {
        ...ProductCatalogPurchaseOrderLine.props,
        min_qty: { type: Number, optional: true },
        packaging: { type: Object, optional: true },
        purchase_uom: { type: Object, optional: true },
        uom: Object,
    };

    get highlightUoM() {
        return true;
    }

    addPackagingQty() {
        this.env.updatePackagingQuantity(this.props.packaging);
    }
}
