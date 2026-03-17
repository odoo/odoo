import { patch } from "@web/core/utils/patch";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { navigateToOdoolinkFromChart } from "../odoo_chart/odoo_chart_helpers";

patch(spreadsheet.components.ScorecardChart.prototype, {
    async navigateToOdooLink(newWindow) {
        await navigateToOdoolinkFromChart(this.env, this.props.chartId, newWindow);
    },
    get hasOdooLink() {
        return this.env.model.getters.getChartOdooLink(this.props.chartId) !== undefined;
    },
    async onClick() {
        if (this.env.model.getters.isDashboard() && this.hasOdooLink) {
            await this.navigateToOdooLink();
        }
    },
});

patch(spreadsheet.components.GaugeChartComponent.prototype, {
    async navigateToOdooLink(newWindow) {
        await navigateToOdoolinkFromChart(this.env, this.props.chartId, newWindow);
    },
    get hasOdooLink() {
        return this.env.model.getters.getChartOdooLink(this.props.chartId) !== undefined;
    },
    async onClick() {
        if (this.env.model.getters.isDashboard() && this.hasOdooLink) {
            await this.navigateToOdooLink();
        }
    },
});
