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

    // Adds 1 OR suggested_qty if it is > pricelist_min_qty ELSE pricelist_min_qty
    addProduct() {
        const { min_qty = 1, suggested_qty = 0 } = this.productCatalogData;
        Math.max(min_qty, suggested_qty) > 0
            ? super.addProduct(Math.max(min_qty, suggested_qty))
            : super.addProduct(1); // Don't add 0 if a vendor pricelist min_qty = 0;
    }
}
