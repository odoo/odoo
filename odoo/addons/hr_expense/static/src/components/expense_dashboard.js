/** @odoo-module */

import { useService } from '@web/core/utils/hooks';
import { formatMonetary } from "@web/views/fields/formatters";
import { Component, onWillStart, useState } from "@odoo/owl";

export class ExpenseDashboard extends Component {

    setup() {
        super.setup();
        this.orm = useService('orm');

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
}
ExpenseDashboard.template = 'hr_expense.ExpenseDashboard';
