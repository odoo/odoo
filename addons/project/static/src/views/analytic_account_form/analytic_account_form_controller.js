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

    async saveButtonClicked(params = {}) {
        if (this.model.root._changes['plan_id'] === undefined) {
            return super.saveButtonClicked(params);
        }
        const projects = await this.orm.call("project.project", "get_project_from_account", [[this.props.resId]]);
        if (!projects){
            return super.saveButtonClicked(params);
        }
        let body = "Changing the plan for this analytic account will unlink it from its associated projects.\n";
        if (projects['account_id'].length > 0) {
            const projectList = projects['account_id'].map((project) => '\t- ' + project).join('\n');
            body = body.concat("This will disable timesheets and make profitability details for the projects unavailable.\n" + projectList  + "\n");
        } else {
            const projectList = projects['other_plan'].map((project) => '\t- ' + project).join('\n');
            body = body.concat(projectList + "\n");
        }
        body = body.concat("Are you sure you want to proceed ?");
        this.dialogService.add(ConfirmationDialog, {
            body: _t(body),
            confirmLabel: _t("confirm"),
            confirm: async () => {
                await this.orm.call("project.project", "remove_account_from_projects", [[this.props.resId]]);
                super.saveButtonClicked(params);
            },
            cancelLabel: _t("Discard"),
            cancel: () => { },
        });
    }

}
