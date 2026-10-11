import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ProjectProjectFormController } from "@project/views/project_form/project_project_form_controller";

patch(ProjectProjectFormController.prototype, {
    async onWillSaveRecord(record) {
        const hadAccount = !!record._values.account_id;
        const hasAccount = !!record.data.account_id;
        const timesheetsEnabled = record.data.allow_timesheets;
        if (hadAccount && !hasAccount && timesheetsEnabled) {
            const confirmed = await new Promise((resolve) => {
                this.dialogService.add(ConfirmationDialog, {
                    title: _t("Warning"),
                    body: _t(
                        "The Timesheets feature requires an analytic account for the Project plan. Removing it will disable the feature. Are you sure you want to continue?"
                    ),
                    confirmLabel: _t("Proceed"),
                    cancelLabel: _t("Cancel"),
                    confirm: () => resolve(true),
                    cancel: () => resolve(false),
                });
            });
            if (!confirmed) {
                return false;
            }
        }
        return super.onWillSaveRecord(...arguments);
    },
});
