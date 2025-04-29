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
            const chartType = this.env.model.getters.getChart(this.props.figureUI.id).type;
            console.log("createChart", chartType);
            if (this.animationStore.animationPlayed[this.props.figureUI.id] !== chartType) {
                chartData = this.enableAnimationInChartData(chartData);
                this.animationStore.disableAnimationForChart(this.props.figureUI.id, chartType);
            }
        }
        super.createChart(chartData);
    },
    updateChartJs(chartData) {
        if (this.env.model.getters.isDashboard()) {
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
        console.log("enableAnimationInChartData");
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
});
