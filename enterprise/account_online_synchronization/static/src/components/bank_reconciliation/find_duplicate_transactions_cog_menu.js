import { Component } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * 'Find Duplicate Transactions' menu
 *
 * This component is used to open a wizard allowing the user to find duplicate
 * transactions since a specific date.
 * It's only available in the bank reconciliation widget.
 * By default, if there is only one selected journal, this journal is directly selected.
 * In case there is no selected journal or more than one, we let the user choose.
 * @extends Component
 */
export class FindDuplicateTransactions extends Component {
    static template = "account_online_synchronization.FindDuplicateTransactions";
    static components = { DropdownItem };
    static props = {};

    setup() {
        this.action = useService("action");
    }

    //---------------------------------------------------------------------
    // Protected
    //---------------------------------------------------------------------

    async openFindDuplicateTransactionsWizard() {
        const { context } = this.env.searchModel;
        const activeModel = context.active_model;
        let activeIds = [];
        if (activeModel === "account.journal") {
            activeIds = context.active_ids;
        } else if (context.default_journal_id) {
            activeIds = context.default_journal_id;
        }
        return this.action.doActionButton({
            type: "object",
            resModel: "account.journal",
            name:"action_open_duplicate_transaction_wizard",
            resIds: activeIds,
        })
    }
}

export const findDuplicateTransactionItem = {
    Component: FindDuplicateTransactions,
    groupNumber: 5, // same group as fetch missing transactions
    isDisplayed: ({ config, isSmall }) => {
        return (
            !isSmall &&
            config.actionType === "ir.actions.act_window" &&
            ["kanban", "list"].includes(config.viewType) &&
            ["bank_rec_widget_kanban", "bank_rec_list"].includes(config.viewSubType)
        )
    },
};

registry.category("cogMenu").add(
    "find-duplicate-transaction-menu",
    findDuplicateTransactionItem,
    { sequence: 3 }, // after fetch missing transactions
);
