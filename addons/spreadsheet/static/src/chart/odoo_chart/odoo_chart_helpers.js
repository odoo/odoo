import { _t } from "@web/core/l10n/translation";

export async function navigateToOdooMenu(menu, actionService, notificationService, newWindow) {
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
    await actionService.doAction(menu.actionID, { newWindow });
}
