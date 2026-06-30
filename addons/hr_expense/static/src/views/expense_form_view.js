import { _t } from "@web/core/l10n/translation";
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
    }

    /**
     * @override
     */
    async beforeExecuteActionButton(clickParams) {
        const record = this.model.root;
        if (
            clickParams.name === "action_submit" &&
            record.data.duplicate_expense_ids.count
        ) {
            await record.save();
            return new Promise((resolve) => {
                this.dialogService.add(ConfirmationDialog, {
                    body: _t("An expense of same category, amount and date already exists."),
                    confirm: async () => {
                        await this.orm.call("hr.expense", "action_approve_duplicates", [record.resId]);
                        resolve(true);
                    },
                }, {
                    onClose: resolve.bind(null, false),
                });
            });
        }
        return super.beforeExecuteActionButton(...arguments);
    }
}

export const ExpenseFormView = {
    ...formView,
    Controller: ExpenseFormController,
};

registry.category("views").add("hr_expense_form_view", ExpenseFormView);
