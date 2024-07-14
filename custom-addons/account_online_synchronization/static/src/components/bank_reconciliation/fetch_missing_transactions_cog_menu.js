/** @odoo-module **/

import { Component } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const cogMenuRegistry = registry.category("cogMenu");

/**
 * 'Fetch Missing Transactions' menu
 *
 * This component is used to open a wizard allowing the user to fetch their missing/pending
 * transaction since a specific date.
 * It's only available in the bank reconciliation widget.
 * By default, if there is only one selected journal, this journal is directly selected.
 * In case there is no selected journal or more than one, we let the user choose which
 * journal he/she wants. This part is handled by the server.
 * @extends Component
 */
export class FetchMissingTransactions extends Component {
    static template = "account_online_synchronization.FetchMissingTransactions";
    static components = { DropdownItem };

    setup() {
        this.action = useService("action");
    }

    //---------------------------------------------------------------------
    // Protected
    //---------------------------------------------------------------------

    async openFetchMissingTransactionsWizard() {
        const { context } = this.env.searchModel;
        const activeModel = context.active_model;
        let activeIds = [];
        if (activeModel === "account.journal") {
            activeIds = context.active_ids;
        } else if (!!context.default_journal_id) {
            activeIds = context.default_journal_id;
        }
        // We have to use this.env.services.orm.call instead of using useService
        // for a specific reason. useService implies that function calls with
        // are "protected", it means that if the component is closed the
        // response will be pending and the code stop their execution.
        // By passing directly from the env, this protection is not activated.
        const action = await this.env.services.orm.call(
            "account.journal",
            "action_open_missing_transaction_wizard",
            [activeIds]
        );
        return this.action.doAction(action);
    }
}

export const fetchMissingTransactionItem = {
    Component: FetchMissingTransactions,
    groupNumber: 5,
    isDisplayed: ({ config, isSmall }) => {
        return !isSmall &&
        config.actionType === "ir.actions.act_window" &&
        ["kanban", "list"].includes(config.viewType) &&
        ["bank_rec_widget_kanban", "bank_rec_list"].includes(config.viewSubType);
    },
};

cogMenuRegistry.add("fetch-missing-transaction-menu", fetchMissingTransactionItem, { sequence: 1 });
