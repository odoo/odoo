import { ProductCatalogKanbanRecord } from "@product/product_catalog/kanban_record";
import { ProductCatalogPurchaseSuggestOrderLine } from "./purchase_order_line";

export class ProductCatalogPurchaseSuggestKanbanRecord extends ProductCatalogKanbanRecord {
    /* Hides suggest line if suggest_qty == qty in PO */
    getCardClasses(...args) {
        const classes = super.getCardClasses(args) || "";
        const catalogData = this.productCatalogData || {};

        if (catalogData.suggested_qty && catalogData.suggested_qty == catalogData.quantity) {
            return classes + " o_hide_suggest_qty";
        }
        return classes;
    }

    get orderLineComponent() {
        return ProductCatalogPurchaseSuggestOrderLine;
    }

    /** Add suggested_qty if greater than requested quantity. */
    addProduct(qty = 1) {
        if (this.productCatalogData.quantity === 0 && qty < this.productCatalogData.suggested_qty) {
            qty = this.productCatalogData.suggested_qty; // Take minimum quantity when trying to add less.
        }
        super.addProduct(qty);
    }
}
