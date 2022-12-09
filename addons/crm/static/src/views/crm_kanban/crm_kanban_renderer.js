/** @odoo-module **/

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { useService } from "@web/core/utils/hooks";

const { onWillStart } = owl;

export class CrmKanbanRenderer extends KanbanRenderer {
    setup() {
        super.setup();
        this.user = useService("user");

        this.showRecurringRevenue = false;
        onWillStart(async () => {
            this.showRecurringRevenue =
                this.props.list.model.progressAttributes.recurring_revenue_sum_field &&
                (await this.user.hasGroup("crm.group_use_recurring_revenues"));
        });
    }

    getRecurringRevenueGroupAggregate(group) {
        const rrField = this.props.list.model.progressAttributes.recurring_revenue_sum_field;
        const value = group.getAggregates(rrField.name);
        const title = rrField.string || this.env._t("Count");
        let currency = false;
        if (value && rrField.currency_field && group.list.records.length) {
            currency = group.list.records[0].data[rrField.currency_field];
        }
        return { value, currency, title };
    }
}
CrmKanbanRenderer.template = "crm.CrmKanbanRenderer";
