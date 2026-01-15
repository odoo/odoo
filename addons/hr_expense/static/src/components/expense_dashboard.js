import { useService } from '@web/core/utils/hooks';
import { formatMonetary } from "@web/views/fields/formatters";
import { Component, onWillStart, useState } from "@odoo/owl";

export class ExpenseDashboard extends Component {
    static template = "hr_expense.ExpenseDashboard";
    static props = {};

    setup() {
        super.setup();
        this.orm = useService('orm');
        this.actionService = useService("action");

        this.state = useState({
            expenses: {}
        });

        onWillStart(async () => {
            const expense_states = await this.orm.call("hr.expense", 'get_expense_dashboard', []);
            this.state.expenses = expense_states;
        });
    }

    renderMonetaryField(value, currency_id) {
        return formatMonetary(value, { currencyId: currency_id});;
    }

    async applyFilter(filterName) {
        const { actionId } = this.env.config;
        const action = actionId ? await this.actionService.loadAction(actionId) : {};

        action['context'] = { [`search_default_${filterName}`]: 1, [`search_default_my_open_expenses`]: 1 };
        return this.actionService.doAction(action, {clearBreadcrumbs: true});
    }
}
