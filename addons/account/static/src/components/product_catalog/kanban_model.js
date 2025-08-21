import { ProductCatalogKanbanModel } from "@product/product_catalog/kanban_model";
import { patch } from "@web/core/utils/patch";

patch(ProductCatalogKanbanModel.prototype, {
    async _loadData(params) {
        const selectedSection = this.env.searchModel.selectedSection;
        if (selectedSection.filtered) {
            params = {
                ...params,
                domain: [...(params.domain || []), ['is_in_selected_section_of_order', '=', true]],
                context: {
                    ...params.context,
                    section_id: selectedSection.sectionId,
                },
            };
        }
        return await super._loadData(params);
    },

    _getOrderLinesInfoParams(params, productIds) {
        return {
            ...super._getOrderLinesInfoParams(params, productIds),
            section_id: this.env.searchModel.selectedSection.sectionId,
        };
    }
})
