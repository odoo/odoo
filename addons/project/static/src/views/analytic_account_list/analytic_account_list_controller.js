import { _t } from "@web/core/l10n/translation";
import { ListController } from "@web/views/list/list_controller";

export class AnalyticAccountListController extends ListController {
    get archiveDialogProps() {
        let dialogProps = super.archiveDialogProps;
        const selectedRecords = this.model.root.selection;

        if (selectedRecords.length) {
            const analyticAccountWithProjects = selectedRecords
                .filter((record) => record.data.project_count)
                .map((record) => record.data.name);
            if (analyticAccountWithProjects.length) {
                dialogProps = {
                    ...dialogProps,
                    body: _t(
                        "Some of the selected analytic accounts are associated with a project:\n%(accountList)s\n\nArchiving these accounts will remove the option to log timesheets for their respective projects.\n\nAre you sure you want to proceed?",
                        {
                            accountList: analyticAccountWithProjects
                                .map((name) => `\t- ${name}`)
                                .join("\n"),
                        }
                    ),
                    confirmLabel: _t("Archive Accounts"),
                    cancelLabel: _t("Discard"),
                };
            }
        }
        return dialogProps;
    }
}
