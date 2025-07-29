import { components } from "@odoo/o-spreadsheet";
import { patch } from "@web/core/utils/patch";

patch(components.ChartJsComponent.prototype, {
    createChart(chartData) {
        if (this.env.model.getters.isDashboard()) {
            chartData = this.addOdooMenuPluginToChartData(chartData);
        }
        super.createChart(chartData);
    },
    updateChartJs(chartData) {
        if (this.env.model.getters.isDashboard()) {
            chartData = this.addOdooMenuPluginToChartData(chartData);
        }
        super.updateChartJs(chartData);
    },
    addOdooMenuPluginToChartData(chartData) {
        chartData.chartJsConfig.options.plugins.chartOdooMenuPlugin = {
            env: this.env,
            menu: this.env.model.getters.getChartOdooMenu(this.props.chartId),
        };
        return chartData;
    },
});
