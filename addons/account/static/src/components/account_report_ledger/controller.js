/** @odoo-module native */
import { AccountReportController } from "@account/components/account_report/controller";
import { patch } from "@web/core/utils/patch";

patch(AccountReportController.prototype, {
    async openBudget(budget) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "account.report.budget",
            res_id: budget.id,
            views: [[false, "form"]],
        });
    },
});
