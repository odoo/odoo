import { ProductCatalogKanbanModel } from "@product/product_catalog/kanban_model";
import { patch } from "@web/core/utils/patch";

patch(ProductCatalogKanbanModel.prototype, {
    async _loadData(params) {
        if (this.env.searchModel.filterBySection) {
            params = {
                ...params,
                domain: [...(params.domain || []), ['catalog_is_in_selected_section', '=', true]],
                context: {
                    ...params.context,
                    section_id: this.env.searchModel.selectedSectionId,
                },
            };
        }
        return await super._loadData(params);
    },

    _getOrderLinesInfoParams(params, productIds) {
        return {
            ...super._getOrderLinesInfoParams(params, productIds),
            section_id: this.env.searchModel.selectedSectionId,
        };
    }
})
