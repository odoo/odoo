import { ProductCatalogKanbanModel } from "@product/product_catalog/kanban_model";

export class PurchaseSuggestCatalogKanbanModel extends ProductCatalogKanbanModel {
    // Patch to pass the context to purchase.order model
    _getOrderLinesInfoParams(loadParams, productIds) {
        const base = super._getOrderLinesInfoParams(loadParams, productIds);
        const suggestCtx = this.config.context || {}; // Controller sets context in config
        return { ...base, ...suggestCtx };
    }
}
