import { patch } from "@web/core/utils/patch";

import { ForecastedHeader as Parent } from "@stock/stock_forecasted/forecasted_header";

export class StockAccountForecastedHeader extends Parent {
    static template = "stock_account.ForecastedHeader";
}

patch(Parent.prototype, {
    _onClickValuation() {
        return this.action.doAction(
            "stock_account.stock_move_valuation_action",
            this._getActionContext()
        );
    },

    _getActionContext() {
        const { product_variants_ids, multiple_product, product_templates } = this.props.docs;
        const context = {
            search_default_incoming: 1,
            search_default_remaining: 1,
            warehouse_id: this.action.currentController.action.context.warehouse_id,
        };
        const actionContext = { additionalContext: context };
        if (!multiple_product) {
            context.search_default_product_id = product_variants_ids[0];
        } else {
            actionContext.props = {
                dynamicFilters: [
                    {
                        description: product_templates[0].display_name,
                        domain: [["product_id", "in", product_variants_ids]],
                    },
                ],
            };
        }
        return actionContext;
    },
});
