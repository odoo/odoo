import { openScheduleMeeting } from "@calendar/core/web/schedule_meeting";
import {
    MENU_TABS,
    MessagingMenu,
} from "@mail/core/public_web/messaging_menu/messaging_menu_model";
import { patchModel } from "@mail/model/export";

import { _t } from "@web/core/l10n/translation";

/**
 * Planning a meeting ahead is offered next to starting one right away. Only in the webclient:
 * it leaves for the calendar, which the public Discuss page has no action for.
 *
 * @type {import("models").MessagingMenu}
 */
export const messagingMenuModelPatch = patchModel(MessagingMenu, {
    /** @override */
    extraTabActions(tabId) {
        const actions = super.extraTabActions(...arguments);
        if (tabId !== MENU_TABS.MEETING) {
            return actions;
        }
        return [
            ...actions,
            {
                id: "schedule_meeting",
                text: _t("Schedule for later"),
                onClick: () => openScheduleMeeting(this.store.env),
            },
        ];
    },
});
