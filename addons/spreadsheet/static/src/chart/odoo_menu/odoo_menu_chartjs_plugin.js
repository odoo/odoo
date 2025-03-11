import { _t } from "@web/core/l10n/translation";

export const chartOdooMenuPlugin = {
    id: "chartOdooMenuPlugin",
    afterEvent(chart, { event }, { env, menu }) {
        const isDashboard = env.model.getters.isDashboard();
        if (!menu || !isDashboard || event.type !== "click" || event.native.defaultPrevented) {
            return;
        }
        navigateToOdooMenu(menu, env.services.action, env.services.notification);
    },
};

export async function navigateToOdooMenu(menu, actionService, notificationService) {
    if (!menu) {
        throw new Error(`Cannot find any menu associated with the chart`);
    }
    if (!menu.actionID) {
        notificationService.add(
            _t(
                "The menu linked to this chart doesn't have an corresponding action. Please link the chart to another menu."
            ),
            { type: "danger" }
        );
        return;
    }
    await actionService.doAction(menu.actionID);
}
