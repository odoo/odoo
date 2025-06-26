/** @odoo-module */
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

    addProduct() {
        if (this.productCatalogData.quantity === 0 && this.productCatalogData.min_qty) {
            super.addProduct(this.productCatalogData.min_qty);
        } else {
            super.addProduct(...arguments);
        }
    },
})
