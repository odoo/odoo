import {
    navigateToOdooMenu,
    isMiddleClick,
} from "@spreadsheet/chart/odoo_chart/odoo_chart_helpers";

export const chartOdooMenuPlugin = {
    id: "chartOdooMenuPlugin",
    afterEvent(chart, { event }, { env, menu }) {
        const isDashboard = env.model.getters.isDashboard();
        const middleClick = isMiddleClick(event);
        if (
            (event.type !== "click" && !middleClick) ||
            !menu ||
            !isDashboard ||
            event.native.defaultPrevented
        ) {
            return;
        }
        navigateToOdooMenu(menu, env.services.action, env.services.notification, middleClick);
    },
};
