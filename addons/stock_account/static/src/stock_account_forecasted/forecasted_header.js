import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import { ForecastedHeader as Parent } from "@stock/stock_forecasted/forecasted_header";

export class StockAccountForecastedHeader extends Parent {
    static template = "stock_account.ForecastedHeader";
}

patch(Parent.prototype, {
    async _onClickValuation() {
        const context = this._getActionContext();
        return this.action.doAction({
            name: _t('Stock Valuation'),
            res_model: 'stock.move',
            type: 'ir.actions.act_window',
            view_mode: 'list,form',
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
            context: context,
        });
    },

    _getActionContext() {
        const context = { ...this.context };
        const templates = this.props.docs.product_templates_ids;
        if (templates) {
            context.search_default_product_tmpl_id = templates;
        } else {
            context.search_default_product_id = this.props.docs.product_variants_ids;
        }
        return context;
    }
});
