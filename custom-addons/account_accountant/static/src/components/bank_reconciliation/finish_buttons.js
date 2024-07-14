/** @odoo-module **/
import { Component, useState } from "@odoo/owl";

export class BankRecFinishButtons extends Component {
    static template = "account_accountant.BankRecFinishButtons";
    static props = {};

    setup() {
        this.breadcrumbs = useState(this.env.config.breadcrumbs);
    }

    getJournalFilter() {
        // retrieves the searchModel's searchItem for the journal
        return Object.values(this.searchModel.searchItems).filter(i => i.type == "field" && i.fieldName == "journal_id")[0];
    }

    get searchModel() {
        return this.env.searchModel;
    }

    get otherFiltersActive() {
        const facets = this.searchModel.facets;
        const journalFilterItem = this.getJournalFilter();
        for (const facet of facets) {
            if (facet.groupId !== journalFilterItem.groupId) {
                return true;
            }
        }
        return false;
    }

    clearFilters() {
        const facets = this.searchModel.facets;
        const journalFilterItem = this.getJournalFilter();
        for (const facet of facets) {
            if (facet.groupId !== journalFilterItem.groupId) {
                this.searchModel.deactivateGroup(facet.groupId);
            }
        }
    }

    breadcrumbBackOrDashboard() {
        if (this.breadcrumbs.length > 1) {
            this.env.services.action.restore();
        } else {
            this.env.services.action.doAction("account.open_account_journal_dashboard_kanban", {clearBreadcrumbs: true});
        }
    }
}
