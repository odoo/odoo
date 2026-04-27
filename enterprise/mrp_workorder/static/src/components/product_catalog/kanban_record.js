/** @odoo-module **/

import { ProductCatalogKanbanRecord } from "@product/product_catalog/kanban_record";
import { patch } from "@web/core/utils/patch";
import { KanbanRecord } from "@web/views/kanban/kanban_record";

patch(ProductCatalogKanbanRecord.prototype, {
    _getUpdateQuantityAndGetPriceParams() {
        return {
            ...super._getUpdateQuantityAndGetPriceParams(),
            from_shop_floor: this.props.record.context.from_shop_floor,
        };
    },

    _updateQuantity() {
        const result = super._updateQuantity();
        this.props.pushCatalogKanbanUpdate?.(result);
    },
});

patch(ProductCatalogKanbanRecord, {
    props: [...KanbanRecord.props, "pushCatalogKanbanUpdate?"],
});
