import { components } from "@odoo/o-spreadsheet";
import { patch } from "@web/core/utils/patch";

patch(components.FullScreenChart.prototype, {
    get hasOdooLink() {
        return this.figureUI && this.env.model.getters.getChartOdooLink(this.chartId) !== undefined;
    },
});
