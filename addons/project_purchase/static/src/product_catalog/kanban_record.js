import { patch } from "@web/core/utils/patch";

import { ProductCatalogKanbanRecord } from "@product/product_catalog/kanban_record";

patch(ProductCatalogKanbanRecord.prototype, {
    _getUpdateCatalogQuantityParams() {
        return {
            ...super._getUpdateCatalogQuantityParams(),
            project_id: this.props.record.context.project_id,
        };
    },
});
