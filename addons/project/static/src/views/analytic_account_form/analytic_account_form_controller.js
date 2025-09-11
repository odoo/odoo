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
        if (this.model.root._changes['plan_id'] === undefined || this.formInDialog || !this.props.resId) {
            return super.saveButtonClicked(params);
        }
        const projectsName = await this.orm.call("project.project", "get_projects_name_from_account", [[this.props.resId], this.model.root._changes['plan_id'][0]]);
        if (!projectsName){
            return super.saveButtonClicked(params);
        }
        let body = "Changing the plan for this analytic account will unlink it from its associated projects.\n";
        if (projectsName['account_id'].length) {
            const projectsNameList = projectsName['account_id'].map((name) => '\t- ' + name).join('\n');
            body = body.concat("This will disable timesheets and make profitability details for the following projects unavailable:\n" + projectsNameList  + "\n");
        } else {
            const projectsNameList = projectsName['other_plan'].map((name) => '\t- ' + name).join('\n');
            body = body.concat(projectsNameList + "\n");
        }
        body = body.concat("Are you sure you want to proceed ?");
        this.dialogService.add(ConfirmationDialog, {
            body: _t(body),
            confirmLabel: _t("Confirm"),
            confirm: async () => {
                await this.orm.call("project.project", "remove_accounts_from_projects", [[this.props.resId], this.model.root._changes['plan_id'][0]]);
                super.saveButtonClicked(params);
            },
            cancelLabel: _t("Discard"),
            cancel: () => { },
        });
    }

}
