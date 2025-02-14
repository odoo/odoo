/** @odoo-module **/
import { registry } from "@web/core/registry";
import { onWillStart } from "@odoo/owl";
import { SearchModel } from "@web/search/search_model";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { listView } from '@web/views/list/list_view';

export class AccountAnalyticSearchModel extends SearchModel {
    setup(services) {
        super.setup(services);

        onWillStart(async () => {
            this.fiscalDateFrom = await this.orm.call(
                'res.company',
                'get_last_fiscal_year',
                [0],
            )
                .then((dateRange) => dateRange)
                // Just in case the get_last_fiscal_year route doesn't exist or is not reachable
                .catch(() => false);

            if (!this.searchDomain || this.searchDomain.length === 0) {
                const lastFiscalYearDateFrom = new Date(this.fiscalDateFrom);
                await this.splitAndAddDomain([
                    ['date', '>=', lastFiscalYearDateFrom.toISOString().split('T')[0]]]
                );
            }
        });
    }
}

const accountListView = {
    ...listView,
    SearchModel: AccountAnalyticSearchModel,
};

registry.category("views").add("account_analytic_list", accountListView);

const accountKanbanView = {
    ...kanbanView,
    SearchModel: AccountAnalyticSearchModel,
};

registry.category("views").add("account_analytic_kanban", accountKanbanView);
