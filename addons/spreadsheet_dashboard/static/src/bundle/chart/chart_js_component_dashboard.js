import { components, stores, helpers } from "@odoo/o-spreadsheet";
import { patch } from "@web/core/utils/patch";

const { useStore, SpreadsheetStore } = stores;
const { deepEquals } = helpers;

class ChartAnimationStore extends SpreadsheetStore {
    animationPlayed = {};

    disableAnimationForChart(chartId) {
        this.animationPlayed[chartId] = true;
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
            if (!this.animationStore.animationPlayed[this.props.figureUI.id]) {
                chartData = this.enableAnimationInChartData(chartData);
                this.animationStore.disableAnimationForChart(this.props.figureUI.id);
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
            this.getChartDataInRuntime(this.currentRuntime),
            this.getChartDataInRuntime(this.chartRuntime)
        );
    },
    getChartDataInRuntime(runtime) {
        const data = runtime.chartJsConfig.data;
        return {
            labels: data.labels,
            dataset: data.datasets.map((dataset) => ({
                data: dataset.data,
                label: dataset.label,
                tree: dataset.tree,
            })),
        };
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
