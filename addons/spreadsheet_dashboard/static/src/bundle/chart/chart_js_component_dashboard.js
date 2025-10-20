import { components } from "@odoo/o-spreadsheet";
import { patch } from "@web/core/utils/patch";

patch(components.ChartJsComponent.prototype, {
    createChart(chartData) {
        if (this.env.model.getters.isDashboard()) {
            chartData = this.addOdooDataSourcePluginToChartData(chartData);
        }
        super.createChart(chartData);
    },
    updateChartJs(chartData) {
        if (this.env.model.getters.isDashboard()) {
            chartData = this.addOdooDataSourcePluginToChartData(chartData);
        }
        super.updateChartJs(chartData);
    },
    addOdooDataSourcePluginToChartData(chartData) {
        chartData.chartJsConfig.options.plugins.chartOdooLinkPlugin = {
            env: this.env,
            chartId: this.props.chartId,
        };
        return chartData;
    },
});
