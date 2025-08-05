import {
    navigateToOdooDatasourceFromChart,
    isChartJSMiddleClick,
} from "@spreadsheet/chart/odoo_chart/odoo_chart_helpers";

export const chartOdooDataSourcePlugin = {
    id: "chartOdooDataSourcePlugin",
    afterEvent(chart, { event }, { env, chartId }) {
        const isDashboard = env?.model.getters.isDashboard();
        const middleClick = isChartJSMiddleClick(event);
        if (
            (event.type !== "click" && !middleClick) ||
            !chartId ||
            !isDashboard ||
            event.native.defaultPrevented
        ) {
            return;
        }
        navigateToOdooDatasourceFromChart(env, chartId, middleClick);
    },
};
