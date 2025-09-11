import { ProductCatalogKanbanRecord } from "@product/product_catalog/kanban_record";
import { ProductCatalogPurchaseSuggestOrderLine } from "./purchase_order_line";

export class ProductCatalogPurchaseSuggestKanbanRecord extends ProductCatalogKanbanRecord {
    /* Highlights product card if suggest_qty > 0,
     * hiding suggest line if suggest_qty == qty in PO */
    getRecordClasses(...args) {
        const classes = super.getRecordClasses(args) || "";

        const catalogData = this.productCatalogData || {};
        if (catalogData.suggested_qty) {
            if (catalogData.suggested_qty == catalogData.quantity) {
                return classes + " o_suggest_highlight" + " o_hide_suggest_qty";
            }
            return classes + " o_suggest_highlight";
        }
        return classes;
    }

    get orderLineComponent() {
        return ProductCatalogPurchaseSuggestOrderLine;
    }

    /** Add suggested_qty or pricelist_min_qty (the greater one) if positive, otherwise add 1. */
    addProduct() {
        const { min_qty = 1, suggested_qty = 0 } = this.productCatalogData;
        super.addProduct(Math.max(min_qty, suggested_qty, 1));
    }
}
