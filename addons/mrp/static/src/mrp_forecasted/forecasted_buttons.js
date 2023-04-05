/** @odoo-module **/
import { ForecastedButtons } from "@stock/stock_forecasted/forecasted_buttons";
import { patch } from '@web/core/utils/patch';

const { onWillStart } = owl;

patch(ForecastedButtons.prototype, 'mrp.ForecastedButtons',{
    setup() {
        this._super.apply();
        onWillStart(async () =>{
            const fields = this.resModel === "product.template" ? ['bom_ids'] : ['bom_ids', 'variant_bom_ids'];
            const res = (await this.orm.call(this.resModel, 'read', [this.productId], { fields }))[0];
            this.bomId = res.variant_bom_ids ? res.variant_bom_ids[0] || res.bom_ids[0] : res.bom_ids[0];
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
