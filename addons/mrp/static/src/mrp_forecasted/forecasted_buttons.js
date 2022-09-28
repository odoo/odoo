/** @odoo-module **/
import { ForecastedButtons } from "@stock/stock_forecasted/forecasted_buttons";
import { patch } from '@web/core/utils/patch';

const { onWillStart } = owl;

patch(ForecastedButtons.prototype, 'mrp.ForecastedButtons',{
    setup() {
        this._super.apply();
        onWillStart(async () =>{
            const res = await this.orm.call(this.resModel, 'read', [this.productId], {fields: ['bom_ids']});
            this.bomId = res[0].bom_ids && res[0].bom_ids[0];
        });
    },

    async _onClickBom(){
        return this.actionService.doAction("mrp.action_report_mrp_bom", {
            additionalContext: {
                active_id: this.bomId,
            },
        });
    }
});
