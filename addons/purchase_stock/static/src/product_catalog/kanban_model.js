import { ProductCatalogKanbanModel } from "@product/product_catalog/kanban_model";
import { getSuggestToggleState, toggleFilters, editSuggestContext } from "./utils";

export class PurchaseSuggestCatalogKanbanModel extends ProductCatalogKanbanModel {
    setup() {
        super.setup(...arguments);
        this.firstLoad = true;
    }

    /**
     * @override  to reorder records with suggested_qty > 0 to the top, keeping original order.
     */
    async _loadData(params) {
        const sortBySuggested = (list) => {
            const suggestProducts = list.filter((record) => record.suggested_qty > 0);
            const notSuggestedProducts = list.filter((record) => record.suggested_qty == 0);
            return [...suggestProducts, ...notSuggestedProducts];
        };
        const suggest = getSuggestToggleState(this.config.context.po_state);
        this._suggestOnFirstLoad(suggest, params);
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

    /**
     *  Adds suggest_context and toggles filters if first load with suggest on.
     *  IMPROVE: action_add_from_catalog should pass context and activate filters
     *  using default_search filters (not easy bc toggle state in local storage)
     */
    _suggestOnFirstLoad(suggestToggle, params) {
        if (!this.firstLoad) {
            return;
        }
        const ctx = this.config.context;
        const sm = this.env.searchModel;
        if (suggestToggle.isOn && this.firstLoad) {
            const suggestCtx = {
                suggest_domain: this.env.searchModel.domain,
                suggest_days: ctx.vendor_suggest_days,
                suggest_based_on: ctx.vendor_suggest_based_on,
                suggest_percent: ctx.vendor_suggest_percent,
                warehouse_id: ctx.warehouse_id,
            };
            this.config.context = editSuggestContext(this.config.context, true, suggestCtx);
            sm.globalContext = editSuggestContext(this.config.context, true, suggestCtx);
            toggleFilters(sm, ["suggested", "products_in_purchase_order"], true);
            params.domain = sm.domain; // TODO safer
            this.firstLoad = false;
        }
    }
}
