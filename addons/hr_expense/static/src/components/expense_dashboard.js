/** @odoo-module */

import { useService } from '@web/core/utils/hooks';
import session from 'web.session';

const { Component, onWillStart, useState } = owl;

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
        value = value.toFixed(2);
        const currency = session.get_currency(currency_id);
        if (currency) {
            if (currency.position === "after") {
                value += currency.symbol;
            } else {
                value = currency.symbol + value;
            }
        }
        return value;
    }
}
ExpenseDashboard.template = 'hr_expense.ExpenseDashboard';
