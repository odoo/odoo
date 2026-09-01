import { useService } from '@web/core/utils/hooks';
import { formatMonetary } from "@web/views/fields/formatters";
import { Component, onWillStart, useState, onWillUpdateProps } from "@odoo/owl";

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
            await this.fetchExpenseDashboardData();
        });

        onWillUpdateProps(async () => {
            await this.fetchExpenseDashboardData();
        });
    }

    renderMonetaryField(value, currency_id) {
        return formatMonetary(value, { currencyId: currency_id});;
    }

    async fetchExpenseDashboardData() {
        const domain = this.env.searchModel?.domain ?? [];
        const expense_states = await this.orm.call(
            "hr.expense",
            'get_expense_dashboard',
            [],
            { context: { domain: domain }}
        );

        this.state.expenses = expense_states;
    }
}
