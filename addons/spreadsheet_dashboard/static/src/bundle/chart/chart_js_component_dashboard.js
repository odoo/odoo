import {
    components,
    invalidateCFEvaluationCommands,
    invalidateChartEvaluationCommands,
    invalidateEvaluationCommands,
    stores,
} from "@odoo/o-spreadsheet";
import { patch } from "@web/core/utils/patch";

const { useStore, SpreadsheetStore } = stores;

class ChartAnimationStore extends SpreadsheetStore {
    constructor(get) {
        super(get);
        this.animationsEnabled = !this.isDataLoading;
        this.animationPlayed = {};
    }

    handle(cmd) {
        if (!this.getters.isDashboard()) {
            return;
        }
        if (
            invalidateEvaluationCommands.has(cmd.type) ||
            invalidateCFEvaluationCommands.has(cmd.type) ||
            invalidateChartEvaluationCommands.has(cmd.type)
        ) {
            if (!this.isDataLoading) {
                this.animationsEnabled = true;
                this.animationPlayed = {};
            }
        }
    }

    disableAnimationForChart(chartId) {
        this.animationPlayed[chartId] = true;
    }

    get isDataLoading() {
        return this.model.config.custom.odooDataProvider.pendingPromises.size > 0;
    }
}

patch(components.ChartJsComponent.prototype, {
    setup() {
        super.setup();
        if (this.env.model.getters.isDashboard()) {
            this.store = useStore(ChartAnimationStore);
        }
    },
    createChart(chartData) {
        if (this.env.model.getters.isDashboard()) {
            if (this.store.isDataLoading) {
                chartData = { ...chartData, data: {} };
            }
            if (this.store.animationsEnabled && !this.store.animationPlayed[this.props.figure.id]) {
                chartData = this.enableAnimationInChartData(chartData);
                this.store.disableAnimationForChart(this.props.figure.id);
            }
        }
        super.createChart(chartData);
    },
    updateChartJs(chartData) {
        if (this.env.model.getters.isDashboard()) {
            if (this.store.isDataLoading) {
                chartData = { ...chartData, data: {} };
            }
            if (this.store.animationsEnabled && !this.store.animationPlayed[this.props.figure.id]) {
                chartData = this.enableAnimationInChartData(chartData);
                this.store.disableAnimationForChart(this.props.figure.id);
            }
        }
        super.updateChartJs(chartData);
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
