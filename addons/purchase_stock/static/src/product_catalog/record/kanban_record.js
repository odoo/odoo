import { ProductCatalogKanbanRecord } from "@product/product_catalog/kanban_record";
import { ProductCatalogPurchaseSuggestOrderLine } from "./purchase_order_line";
import { useEnv } from "@odoo/owl";

export class ProductCatalogPurchaseSuggestKanbanRecord extends ProductCatalogKanbanRecord {
    setup() {
        super.setup();
        this.suggest = useEnv().suggest;
        this._debouncedKanbanRecompute = useEnv()._debouncedKanbanRecompute;
    }

    /* Highlights product card if suggest_qty > 0,
     * hiding suggest line if suggest_qty == qty in PO */
    getRecordClasses(...args) {
        const classes = super.getRecordClasses(args) || "";

        const catalogData = this.productCatalogData || {};
        if (catalogData.suggested_qty) {
            if (catalogData.suggested_qty == catalogData.quantity) {
                return classes + " o_suggest_highlight o_hide_suggest_qty";
            }
            return classes + " o_suggest_highlight";
        }
        return classes;
    }

    get orderLineComponent() {
        return ProductCatalogPurchaseSuggestOrderLine;
    }

    addProduct() {
        // Add suggested_qty or pricelist_min_qty (the greater one) if positive, otherwise add 1.
        const { min_qty = 1, suggested_qty = 0 } = this.productCatalogData;
        super.addProduct(Math.max(min_qty, suggested_qty, 1));
    }

    async updateQuantity(quantity) {
        await super.updateQuantity(quantity);
        if (quantity === 0 && this.suggest.inTheOrderFilterOn && this.suggest.suggestToggle.isOn) {
            await this._debouncedKanbanRecompute(); // Reload UI to hide product
        }
    }
}
