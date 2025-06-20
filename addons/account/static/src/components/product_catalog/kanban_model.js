import { ProductCatalogKanbanModel } from "@product/product_catalog/kanban_model";
import { patch } from "@web/core/utils/patch";

patch(ProductCatalogKanbanModel.prototype, {
    async _loadData(params) {
        params = this._applySectionFilter(params, {
            sectionFilterField: 'is_in_selected_section_of_move',
            orderModel: 'account.move',
        });
        return await super._loadData(params);
    }
})
