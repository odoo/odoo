/** @odoo-module **/
import { patch } from '@web/core/utils/patch';

import { ForecastedHeader as Parent } from "@stock/stock_forecasted/forecasted_header";

export class StockAccountForecastedHeader extends Parent{}

patch(Parent.prototype, 'stock_account.ForecastedHeader', {
    async _onClickValuation() {
        const context = this._getActionContext();
        return this.action.doAction({
            name: this.env._t('Stock Valuation'),
            res_model: 'stock.valuation.layer',
            type: 'ir.actions.act_window',
            view_mode: 'list,form',
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
            context: context,
        });
    }
});

StockAccountForecastedHeader.template = 'stock_account.ForecastedHeader';
