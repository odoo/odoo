import { ProductCatalogKanbanModel } from "@product/product_catalog/kanban_model";

export class PurchaseProductCatalogKanbanModel extends ProductCatalogKanbanModel {
    async _loadData(params) {
        params = this._applySectionFilter(params, {
            sectionFilterField: 'is_in_selected_section_of_purchase_order',
            orderModel: 'purchase.order',
        });
        return await super._loadData(params);
    }
}
