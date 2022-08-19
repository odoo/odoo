/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

const { useSubEnv } = owl;

export class ExpenseFormController extends FormController {
    setup() {
        super.setup();
        const dialogService = useService("dialog");
        const orm = useService("orm");
        const t = this.env._t;
        const previousOnClickViewButton = this.env.onClickViewButton;
        useSubEnv({
            async onClickViewButton({ clickParams, record}) {
                if (clickParams.name === "action_submit_expenses") {
                    if (record.data.duplicate_expense_ids.count) {
                        dialogService.add(ConfirmationDialog, {
                            body: t("An expense of same category, amount and date already exists."),
                            confirm: async () => {
                                orm.call(
                                    'hr.expense',
                                    'action_approve_duplicates',
                                    [record.data.id],
                                );
                                previousOnClickViewButton({ clickParams, record});
                            },
                            cancel: () => {},
                        });
                    } else {
                        previousOnClickViewButton({ clickParams, record});
                    }
                } else {
                    previousOnClickViewButton({ clickParams, record});
                }
            }
        });
    }
}

export const ExpenseFormView = {
    ...formView,
    Controller: ExpenseFormController,
};

registry.category("views").add('hr_expense_form_view', ExpenseFormView);
