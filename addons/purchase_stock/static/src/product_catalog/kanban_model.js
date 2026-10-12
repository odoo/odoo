import { ProductCatalogKanbanModel } from "@product/product_catalog/kanban_model";
import { getSuggestToggleState } from "./utils";

export class PurchaseSuggestCatalogKanbanModel extends ProductCatalogKanbanModel {
    /**
     * @override  to reorder records with suggested_qty > 0 to the top, keeping original order.
     */
    async _loadData(params) {
        const sortBySuggested = (list) => {
            const suggestProducts = list.filter((record) => record.suggested_qty > 0);
            const notSuggestedProducts = list.filter((record) => record.suggested_qty == 0);
            return [...suggestProducts, ...notSuggestedProducts];
        };
        const suggest = getSuggestToggleState(this.config.context.product_catalog_order_state);
        const result = await super._loadData(params);
        if (!suggest.isOn || !result.records.some((r) => r.suggested_qty > 0)) {
            return result;
        }
        if (!params.isMonoRecord) {
            if (params.groupBy?.length) {
                for (const group of result.groups) {
                    group.list.records = sortBySuggested(group.list.records);
                }
            } else {
                result.records = sortBySuggested(result.records);
            }
        }
        return result;
    }

    /** Pass suggest context to /product/catalog/order_lines_info RPC
     * to add computed ["suggested_qty"] key to productCatalogData */
    _getOrderLinesInfoParams(loadParams, productIds) {
        const base = super._getOrderLinesInfoParams(loadParams, productIds);
        return { ...base, ...loadParams.context };
    }
}
