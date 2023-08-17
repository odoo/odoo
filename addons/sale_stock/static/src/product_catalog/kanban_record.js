/** @odoo-module */
import { ProductCatalogKanbanRecord } from "@sale/js/product_catalog/kanban_record";
import { patch } from "@web/core/utils/patch";

patch(ProductCatalogKanbanRecord.prototype, {
    updateQuantity(quantity) {
        if (
            this.productCatalogData.quantity === this.productCatalogData.deliveredQty &&
            quantity < this.productCatalogData.quantity
        ) {
            // This condition is triggered on the following specific condition that the product was already at the minimum quantity possible,
            // as stated in the sale_stock module, then the user inputs a quantity lower than this limit, in this case we need the record to forcefully update
            // the record
            this.props.record.load();
            this.props.record.model.notify();
        } else {
            super.updateQuantity(Math.max(quantity, this.productCatalogData.deliveredQty));
        }
    },
});
