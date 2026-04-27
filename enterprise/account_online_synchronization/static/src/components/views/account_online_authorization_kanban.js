import { patch } from "@web/core/utils/patch";
import { BankRecKanbanController } from "@account_accountant/components/bank_reconciliation/kanban";

patch(BankRecKanbanController.prototype, {
    setup() {
        super.setup();
        this.displayDuplicateWarning = !!this.props.context.duplicates_from_date;
    },
    async onWarningClick () {
        const { context } = this.env.searchModel;
        return this.action.doActionButton({
            type: "object",
            resModel: "account.journal",
            name:"action_open_duplicate_transaction_wizard",
            resId: this.state.journalId,
            args: JSON.stringify([context.duplicates_from_date]),
        })
    },
})
