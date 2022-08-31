/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class ExpenseFormController extends FormController {
    setup() {
        super.setup();
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
        this.t = this.env._t;
    }

    async beforeExecuteActionButton(clickParams) {
        const record = this.model.root;
        if (
            clickParams.name === "action_submit_expenses" &&
            record.data.duplicate_expense_ids.count
        ) {
            let resolve;
            const prom = new Promise((res) => {
                resolve = res;
            });
            let execActionButton;
            this.dialogService.add(ConfirmationDialog, {
                body: this.env._t("An expense of same category, amount and date already exists."),
                confirm: async () => {
                    this.orm.call("hr.expense", "action_approve_duplicates", [record.resId]);
                    execActionButton = true;
                    resolve();
                },
                cancel: () => {
                    execActionButton = false;
                    resolve();
                },
            });
            await prom;
            return execActionButton;
        }
    }
}

export const ExpenseFormView = {
    ...formView,
    Controller: ExpenseFormController,
};

registry.category("views").add("hr_expense_form_view", ExpenseFormView);
