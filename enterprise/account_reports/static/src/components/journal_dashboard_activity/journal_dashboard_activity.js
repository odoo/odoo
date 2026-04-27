/** @odoo-module */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { JournalDashboardActivity, journalDashboardActivity } from "@account/components/journal_dashboard_activity/journal_dashboard_activity";

export class JournalDashboardActivityTaxReport extends JournalDashboardActivity {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    async openActivity(activity) {
        if (activity.activity_category === 'tax_report') {
            const act = await this.orm.call("mail.activity", "action_open_tax_activity", [activity.id], {});
            this.action.doAction(act);
        } else {
            super.openActivity(activity);
        }
    }
}

export const journalDashboardActivityTaxReport = {
    ...journalDashboardActivity,
    component: JournalDashboardActivityTaxReport,
};

registry
    .category("fields")
    .add("kanban_vat_activity", journalDashboardActivityTaxReport, { force: true });
