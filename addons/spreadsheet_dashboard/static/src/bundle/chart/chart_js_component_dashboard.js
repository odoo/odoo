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
            if (!this.animationStore.animationPlayed[this.props.figure.id]) {
                chartData = this.enableAnimationInChartData(chartData);
                this.animationStore.disableAnimationForChart(this.props.figure.id);
            }
        }
        super.createChart(chartData);
    },
    updateChartJs(chartData) {
        if (this.env.model.getters.isDashboard()) {
            if (this.hasChartDataChanged()) {
                chartData = this.enableAnimationInChartData(chartData);
                this.animationStore.disableAnimationForChart(this.props.figure.id);
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
});
