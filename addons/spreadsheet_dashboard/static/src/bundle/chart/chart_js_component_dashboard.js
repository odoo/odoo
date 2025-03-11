import { components, stores, helpers } from "@odoo/o-spreadsheet";
import { patch } from "@web/core/utils/patch";

const { useStore, SpreadsheetStore } = stores;
const { deepEquals } = helpers;

class ChartAnimationStore extends SpreadsheetStore {
    animationPlayed = {};

    disableAnimationForChart(chartId, chartType) {
        this.animationPlayed[chartId] = chartType;
    }
}

patch(components.ChartJsComponent.prototype, {
    setup() {
        super.setup();
        if (this.env.model.getters.isDashboard()) {
            this.animationStore = useStore(ChartAnimationStore);
        }
    },
    createChart(chartData) {
        if (this.env.model.getters.isDashboard()) {
            chartData = this.addOdooMenuPluginToChartData(chartData);
            const chartType = this.env.model.getters.getChart(this.props.figureUI.id).type;
            if (this.animationStore.animationPlayed[this.props.figureUI.id] !== chartType) {
                chartData = this.enableAnimationInChartData(chartData);
                this.animationStore.disableAnimationForChart(this.props.figureUI.id, chartType);
            }
        }
        super.createChart(chartData);
    },
    updateChartJs(chartData) {
        if (this.env.model.getters.isDashboard()) {
            chartData = this.addOdooMenuPluginToChartData(chartData);
            if (this.hasChartDataChanged()) {
                chartData = this.enableAnimationInChartData(chartData);
                this.animationStore.disableAnimationForChart(this.props.figureUI.id);
            }
        }
        super.updateChartJs(chartData);
    },
    hasChartDataChanged() {
        return !deepEquals(
            this.currentRuntime.chartJsConfig.data,
            this.chartRuntime.chartJsConfig.data
        );
    },
    enableAnimationInChartData(chartData) {
        return {
            ...chartData,
            options: {
                ...chartData.options,
                animation: {
                    animateRotate: true,
                },
            },
        };
    },
    addOdooMenuPluginToChartData(chartData) {
        chartData.options.plugins.chartOdooMenuPlugin = {
            env: this.env,
            menu: this.env.model.getters.getChartOdooMenu(this.props.figureUI.id),
        };
        return chartData;
    },
});
