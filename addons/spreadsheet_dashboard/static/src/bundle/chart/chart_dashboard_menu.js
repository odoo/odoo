import { components } from "@odoo/o-spreadsheet";
import { patch } from "@web/core/utils/patch";

const { ChartDashboardMenu } = components;

patch(ChartDashboardMenu.prototype, {
    get granularityOptions() {
        return this.env.model.getters.getAvailableChartGranularities(this.props.chartId);
    },

    onGranularitySelected(ev) {
        this.env.model.dispatch("UPDATE_CHART_GRANULARITY", {
            chartId: this.props.chartId,
            granularity: ev.target.value,
        });
    },
});
