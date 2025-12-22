import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { FormController } from "@web/views/form/form_controller";

export class AnalyticAccountFormController extends FormController {
    getStaticActionMenuItems() {
        const menuItems = super.getStaticActionMenuItems();
        if (this.model.root.data.project_count) {
            menuItems.archive.callback = async () => {
                const projects = await this.orm.call("project.project", "search_read", [
                    [["account_id", "=", this.props.resId]],
                    ["name"],
                ]);
                this.dialogService.add(ConfirmationDialog, {
                    ...this.archiveDialogProps,
                    body: _t(
                        "This analytic account is associated with the following projects:\n%(projectList)s\n\nArchiving the account will remove the option to log timesheets for these projects.\n\nAre you sure you want to proceed?",
                        {
                            projectList: projects
                                .map((project) => `\t- ${project.name}`)
                                .join(`\n`),
                        }
                    ),
                    confirmLabel: _t("Archive Account"),
                    cancelLabel: _t("Discard"),
                });
            };
        }
        return menuItems;
    }
}
