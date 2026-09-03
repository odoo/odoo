import { useService } from '@web/core/utils/hooks';
import { formatMonetary } from "@web/views/fields/formatters";
import { Component, onWillStart, useState, onWillUpdateProps } from "@odoo/owl";
import { Domain } from "@web/core/domain";

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

    async applyFilter(filterName) {
        const searchModel = this.env.searchModel;

        // Search for active filters implying an expense state
        const stateActiveFilters = searchModel.query.filter(item => {
            const filters = searchModel.searchItems[item.searchItemId];

            if (!filters || !filters.domain) {
                return false;
            }
            try {
                const domain = new Domain(filters.domain).toList();
                return domain.some(tuple => tuple[0] === "state");
            } catch {
                return false;
            }
        });

        // Deactivate the filters implying an expense state
        if (stateActiveFilters) {
            stateActiveFilters.forEach(item => {
                searchModel.toggleSearchItem(item.searchItemId);
            });
        }
        // Toggle the filter corresponding to the current state
        const searchItem = Object.values(searchModel.searchItems).find(
            (searchItem) => searchItem.name === filterName
        );
        searchModel.toggleSearchItem(searchItem.id);
    }
}
