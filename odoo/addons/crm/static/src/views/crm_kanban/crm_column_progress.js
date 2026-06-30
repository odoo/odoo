/** @odoo-module */

import { onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ColumnProgress } from "@web/views/view_components/column_progress";
import { session } from "@web/session";
import { getCurrency } from "@web/core/currency";

export class CrmColumnProgress extends ColumnProgress {
    static props = {
        ...ColumnProgress.props,
        progressBarState: { type: Object },
    };
    static template = "crm.ColumnProgress";
    setup() {
        super.setup();
        this.user = useService("user");
        this.showRecurringRevenue = false;

        onWillStart(async () => {
            if (this.props.progressBarState.progressAttributes.recurring_revenue_sum_field) {
                this.showRecurringRevenue = await this.user.hasGroup("crm.group_use_recurring_revenues");
            }
        });
    }

    getRecurringRevenueGroupAggregate(group) {
        const rrField = this.props.progressBarState.progressAttributes.recurring_revenue_sum_field;
        const aggregatedValue = this.props.progressBarState.getAggregateValue(group, rrField);
        let currency = false;
        if (aggregatedValue.value && rrField.currency_field) {
            currency = getCurrency(session.company_currency_id);
        }
        return { ...aggregatedValue, currency };
    }
}
