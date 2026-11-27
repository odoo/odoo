import { ForecastedButtons } from "@stock/stock_forecasted/forecasted_buttons";
import { patch } from "@web/core/utils/patch";
import { t } from "@odoo/owl";

patch(ForecastedButtons, {
    propShape: {
        ...ForecastedButtons.propShape,
        bomIds: t.object(),
    },
});

patch(ForecastedButtons.prototype, {
    async _onClickBom(){
        return this.actionPlugin.doAction("mrp.action_report_mrp_bom", {
            additionalContext: {
                active_id: this.bomId,
                active_product_id: this.productId,
                active_model: this.resModel,
                mode: "forecast",
            },
        });
    },

    get bomId() {
        return this.props.bomIds?.[this.productId]?.[0] || Object.values(this.props.bomIds || {})[0]?.[0];
    },
});
