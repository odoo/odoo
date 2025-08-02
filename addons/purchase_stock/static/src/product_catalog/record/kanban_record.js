import { ProductCatalogKanbanRecord } from "@product/product_catalog/kanban_record";
import { ProductCatalogPurchaseSuggestOrderLine } from "./purchase_order_line";

export class ProductCatalogPurchaseSuggestKanbanRecord extends ProductCatalogKanbanRecord {
    getRecordClasses(...args) {
        const classes = super.getRecordClasses(args) || "";
        if (this.productCatalogData?.suggested_qty) {
            return classes + " o_suggest_purchase"; // Same as o_product_added
        }
        return classes;
    }

    get orderLineComponent() {
        return ProductCatalogPurchaseSuggestOrderLine;
    }

    addProduct() {
        const { min_qty = 1, suggested_qty = 0 } = this.productCatalogData;
        super.addProduct(Math.max(min_qty, suggested_qty));
    }
}
