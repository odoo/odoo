/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PlanningControllerActions } from "@planning/views/planning_hooks";
import { Domain } from "@web/core/domain";


patch(PlanningControllerActions.prototype, {
    autoPlanDomain() {
        const domain = super.autoPlanDomain(...arguments);
        return Domain.and([
            domain,
            ["|", ["sale_line_id", "=", false], ["sale_line_id.state", "!=", "cancel"]],
        ]).toList();
    },
    autoPlanSuccessNotification() {
        return _t("Open shifts and sales orders assigned");
    },

    autoPlanFailureNotification() {
        return _t(
            "All open shifts and sales orders have already been assigned, or there are no resources available to take them at this time."
        );
    },

    autoPlanRollbackSuccessNotification() {
        return _t("Open shifts and sales orders unscheduled");
    },
});
