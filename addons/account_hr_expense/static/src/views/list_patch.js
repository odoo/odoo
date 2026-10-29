import { patch } from "@web/core/utils/patch";
import { ExpenseListController } from "@hr_expense/views/list";

patch(ExpenseListController.prototype, {
    get payGroup() {
        return "account.group_account_invoice";
    },

    get actionAdditionalContext() {
        return { ...super.actionAdditionalContext, dont_redirect_to_payments: 1 };
    },

    /** The payment is registered on the journal entry, once posted */
    displayPay() {
        return (
            super.displayPay() &&
            this.model.root.selection.every((record) => record.data.account_move_state === "posted")
        );
    },
});
