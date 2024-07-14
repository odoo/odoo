/** @odoo-module */
import { FSMProductCatalogKanbanRecord } from "@industry_fsm_sale/components/product_catalog/kanban_record";

import { patch } from "@web/core/utils/patch";

patch(FSMProductCatalogKanbanRecord.prototype, {
    updateQuantity(quantity) {
        if (
            this.productCatalogData.quantity === this.productCatalogData.minimumQuantityOnProduct &&
            quantity < this.productCatalogData.quantity
        ) {
            // This condition is only triggered when the product was already at the minimum quantity
            // possible, as stated in the fsm_stock module, then the user inputs a quantity lower
            // than this limit, in this case we need the record to forcefully update the record.
            this.props.record.load();
            this.props.record.model.notify();
        } else {
            super.updateQuantity(Math.max(quantity, this.productCatalogData.minimumQuantityOnProduct));
        }
    },
});
