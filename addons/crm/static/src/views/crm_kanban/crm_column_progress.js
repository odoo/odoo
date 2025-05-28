import { onWillStart } from "@odoo/owl";
import { user } from "@web/core/user";
import { RottingColumnProgress } from "@mail/js/rotting_mixin/rotting_column_progress";

export class CrmColumnProgress extends RottingColumnProgress {
    static template = "crm.ColumnProgress";
    setup() {
        super.setup();
        this.showRecurringRevenue = false;

        onWillStart(async () => {
            if (this.props.progressBarState.progressAttributes.recurring_revenue_sum_field) {
                this.showRecurringRevenue = await user.hasGroup("crm.group_use_recurring_revenues");
            }
        });
    }

    getRecurringRevenueGroupAggregate(group) {
        if (!this.showRecurringRevenue) {
            return {};
        }
        const rrField = this.props.progressBarState.progressAttributes.recurring_revenue_sum_field;
        return this.props.progressBarState.getAggregateValue(group, rrField);
    }
}
