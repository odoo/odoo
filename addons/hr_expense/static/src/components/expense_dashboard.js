import { useState } from "@web/owl2/utils";
import { useService } from '@web/core/utils/hooks';
import { formatMonetary } from "@web/views/fields/formatters";
<<<<<<< 3c7ca86d1719187c6bfe60cefee85bfc59a751cb
import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { Domain } from "@web/core/domain";
||||||| a5424bff9b477b1350456ddd91582399eeaa1fd6
import { Component, onWillStart, useState, onWillUpdateProps } from "@odoo/owl";
import { Domain } from "@web/core/domain";
=======
import { Component, onWillStart, useState, onWillUpdateProps } from "@odoo/owl";
>>>>>>> 3c9ed13042232ce07bf40bfd94e8ee177618559e

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
