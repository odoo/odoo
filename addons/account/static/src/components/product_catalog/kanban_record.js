import { ProductCatalogKanbanRecord } from "@product/product_catalog/kanban_record";
import { ProductCatalogAccountMoveLine } from "./account_move_line";
import { patch } from "@web/core/utils/patch";

patch(ProductCatalogKanbanRecord.prototype, {
    get orderLineComponent() {
        if (this.env.orderResModel === "account.move") {
            return ProductCatalogAccountMoveLine;
        }
        return super.orderLineComponent;
    },

    addProduct(qty = 1) {
        if (this.productCatalogData.quantity === 0 && qty < this.productCatalogData.min_qty) {
            qty = this.productCatalogData.min_qty; // Take seller's minimum if trying to add less
        }
        super.addProduct(qty);
    },
});
