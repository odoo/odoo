import { components } from "@odoo/o-spreadsheet";
import { patch } from "@web/core/utils/patch";

patch(components.ChartJsComponent.prototype, {
    createChart(chartData) {
        super.createChart(this.addOdooMenuPluginToChartData(chartData));
    },
    updateChartJs(chartData) {
        super.updateChartJs(this.addOdooMenuPluginToChartData(chartData));
    },
    addOdooMenuPluginToChartData(chartData) {
        chartData.options.plugins.chartOdooMenuPlugin = {
            env: this.env,
            menu: this.env.model.getters.getChartOdooMenu(this.props.figure.id),
        };
        return chartData;
    },
});
