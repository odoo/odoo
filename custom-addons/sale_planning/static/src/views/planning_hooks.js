/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PlanningControllerActions } from "@planning/views/planning_hooks";


patch(PlanningControllerActions.prototype, {
    autoPlanSuccessNotification() {
        return _t("The open shifts and sales orders have been successfully assigned.");
    },

    autoPlanFailureNotification() {
        return _t(
            "All open shifts and sales orders have already been assigned, or there are no resources available to take them at this time."
        );
    }
});
