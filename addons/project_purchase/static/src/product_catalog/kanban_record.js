/** @odoo-module **/
import { patch } from "@web/core/utils/patch";

import { ProductCatalogKanbanRecord } from "@product/product_catalog/kanban_record";

patch(ProductCatalogKanbanRecord.prototype, {
    _getUpdateQuantityAndGetPriceParams() {
        return {
            ...super._getUpdateQuantityAndGetPriceParams(),
            project_id: this.props.record.context.project_id,
        };
    },
});
