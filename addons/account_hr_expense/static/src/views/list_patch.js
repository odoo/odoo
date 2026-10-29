import { patch } from "@web/core/utils/patch";
import { ExpenseListController } from "@hr_expense/views/list";

patch(ExpenseListController.prototype, {
    get actionAdditionalContext() {
        return { ...super.actionAdditionalContext, dont_redirect_to_payments: 1 };
    },
});
