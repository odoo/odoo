import { ProductCatalogKanbanModel } from "@product/product_catalog/kanban_model";

export class PurchaseSuggestCatalogKanbanModel extends ProductCatalogKanbanModel {
    /* Pass suggest context to /product/catalog/order_lines_info RPC
     * to add computed ["suggested_qty"] key to productCatalogData */
    _getOrderLinesInfoParams(loadParams, productIds) {
        const base = super._getOrderLinesInfoParams(loadParams, productIds);
        const suggestCtx = this.config.context || {}; // Controller sets context in config
        return { ...base, ...suggestCtx };
    }
}
