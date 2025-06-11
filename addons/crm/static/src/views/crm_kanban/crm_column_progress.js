import { onWillStart } from "@odoo/owl";
import { user } from "@web/core/user";
import { getCurrency } from "@web/core/currency";
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
        const rrField = this.props.progressBarState.progressAttributes.recurring_revenue_sum_field;
        const aggregatedValue = this.props.progressBarState.getAggregateValue(group, rrField);
        let currency = false;
        /**
         * As agreggates don't add in the currency for lead aggregates, we fetch it from the current group.
         * Aggregates compute to 0 on lead groups with multiple currencies ; if the value is 0, we do not fetch the currency
         */
        const firstRecord = this.props.group.list.records[0];
        if (aggregatedValue.value && rrField.currency_field && firstRecord && firstRecord.data.company_currency) {
            currency = getCurrency(firstRecord.data.company_currency.id);
        }
        return { ...aggregatedValue, currency };
    }
}
