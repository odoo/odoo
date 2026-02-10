import {
    navigateToOdoolinkFromChart,
    isChartJSMiddleClick,
} from "@spreadsheet/chart/odoo_chart/odoo_chart_helpers";

export const chartOdooLinkPlugin = {
    id: "chartOdooLinkPlugin",
    afterEvent(chart, { event }, { env, chartId }) {
        const odooLink = env?.model.getters.getChartOdooLink(chartId);
        const isDashboard = env?.model.getters.isDashboard();
        if (!odooLink || !isDashboard) {
            return;
        }
        event.native.target.style.cursor = "pointer";

        const middleClick = isChartJSMiddleClick(event);
        if ((event.type !== "click" && !middleClick) || event.native.defaultPrevented) {
            return;
        }
        navigateToOdoolinkFromChart(env, chartId, middleClick);
    },
};
