import { navigateToOdooMenu } from "@spreadsheet/chart/odoo_chart/odoo_chart_helpers";

export const chartOdooMenuPlugin = {
    id: "chartOdooMenuPlugin",
    afterEvent(chart, { event }, { env, menu }) {
        const isDashboard = env.model.getters.isDashboard();
        if (event.type !== "click" || !menu || !isDashboard || event.native.defaultPrevented) {
            return;
        }
        navigateToOdooMenu(menu, env.services.action, env.services.notification);
    },
};
