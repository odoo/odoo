import {
    navigateToOdoolinkFromChart,
    isChartJSMiddleClick,
} from "@spreadsheet/chart/odoo_chart/odoo_chart_helpers";

export const chartOdooLinkPlugin = {
    id: "chartOdooLinkPlugin",
    afterEvent(chart, { event }, { env, chartId }) {
        const odooLink = env?.model.getters.getChartOdooLink(chartId);
        const isDashboard = env?.model.getters.isDashboard();
        event.native.target.style.cursor = odooLink && isDashboard ? "pointer" : "";

        const middleClick = isChartJSMiddleClick(event);
        if (
            (event.type !== "click" && !middleClick) ||
            !chartId ||
            !isDashboard ||
            event.native.defaultPrevented
        ) {
            return;
        }
        navigateToOdoolinkFromChart(env, chartId, middleClick);
    },
};
