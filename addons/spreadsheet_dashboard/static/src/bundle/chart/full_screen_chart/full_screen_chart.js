import { components } from "@odoo/o-spreadsheet";
import { patch } from "@web/core/utils/patch";

patch(components.FullScreenChart.prototype, {
    get hasOdooMenu() {
        return this.chartId && this.env.model.getters.getChartOdooMenu(this.chartId) !== undefined;
    },
});
