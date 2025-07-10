import { patch } from "@web/core/utils/patch";
import { ProductCatalogKanbanRecord } from "@product/product_catalog/kanban_record";
import { KanbanRecord } from "@web/views/kanban/kanban_record";

patch(ProductCatalogKanbanRecord.prototype, {
    getRecordClasses(...args) {
        const classes = KanbanRecord.prototype.getRecordClasses.apply(this, args) || "";

        if (this.productCatalogData?.suggested_qty) {
            return classes + " o_suggest_adding"; // Same as o_product_added
        }
        return classes;
    },

    addProduct() {
        if (this.productCatalogData?.suggested_qty) {
            super.addProduct(this.productCatalogData.suggested_qty);
        } else {
            super.addProduct(...arguments);
        }
    },
});
