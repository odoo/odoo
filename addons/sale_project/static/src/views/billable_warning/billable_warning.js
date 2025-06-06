import { registry } from "@web/core/registry";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

const projectProjectFormView = registry.category("views").get("project_project_form");

export class ConfirmOnSaveNonBillableController extends projectProjectFormView.Controller {
    /**
     * @override
     */
    async onWillSaveRecord(record, changes) {
        let linkedProject = false;

        if ("allow_billable" in changes && changes.allow_billable === false) {
            linkedProject = await record.model.orm.call(
                record.resModel,
                "check_allow_billable_projects",
                [[record.resId]],
            );
        }

        if (linkedProject) {
            const confirmation = await new Promise((resolve) => {
                this.env.services.dialog.add(ConfirmationDialog, {
                    title: _t("Confirmation Required"),
                    body: _t("Making this project non-billable will unlink it from any products that create tasks in it or use it as a template. Are you sure you want to continue?"),
                    confirm: async () => resolve(true),
                    cancel: async () => resolve(false),
                });
            });

            if (!confirmation) {
                record.update({ allow_billable: true });
                return false;
            }
        }

        return super.onWillSaveRecord(...arguments);
    }
}

registry.category("views").add("form_confirm_non_billable", {
    ...registry.category("views").get("form"),
    Controller: ConfirmOnSaveNonBillableController,
});
