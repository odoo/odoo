import { _t } from "@web/core/l10n/translation";
import { ListController } from "@web/views/list/list_controller";
import { AnalyticAccountListConfirmationDialog } from "./analytic_account_list_confirmation_dialog";

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

    async onWillSaveMulti(editedRecord, changes, validSelectedRecords) {
        if (changes['plan_id'] !== undefined) {
            if (this.hasMousedownDiscard) {
                this.nextActionAfterMouseup = () => this.model.root.multiSave(editedRecord);
                return false;
            }
            const { isDomainSelected, selection } = this.model.root;
            return new Promise((resolve) => {
                let ids = [];
                for (const recordId in validSelectedRecords) {
                    ids.push(validSelectedRecords[recordId].evalContext.id);
                }
                const dialogProps = {
                    confirm: () => resolve(true),
                    cancel: () => {
                        if (this.editedRecord) {
                            this.model.root.leaveEditMode({ discard: true });
                        } else {
                            editedRecord.discard();
                        }
                        resolve(false);
                    },
                    isDomainSelected,
                    fields: Object.keys(changes).map((fieldName) => {
                        const fieldNode = Object.values(this.archInfo.fieldNodes).find(
                            (fieldNode) => fieldNode.name === fieldName
                        );
                        const label = fieldNode && fieldNode.string;
                        return {
                            name: fieldName,
                            label: label || editedRecord.fields[fieldName].string,
                            fieldNode,
                            widget: fieldNode && fieldNode.widget,
                        };
                    }),
                    nbRecords: selection.length,
                    nbValidRecords: validSelectedRecords.length,
                    record: editedRecord,
                    accountIdList: ids,
                    projectAccountId : false,
                    projectOtherPlan : false,
                    plan_id : changes['plan_id'],
                };

                const focusedCellBeforeDialog = document.activeElement.closest(".o_data_cell");
                this.dialogService.add(AnalyticAccountListConfirmationDialog, dialogProps, {
                    onClose: () => {
                        if (focusedCellBeforeDialog) {
                            focusedCellBeforeDialog.focus();
                        }
                        this.model.root.leaveEditMode({ discard: true });
                        resolve(false);
                    },
                });
            });
        } else {
            super.onWillSaveMulti(editedRecord, changes, validSelectedRecords);
        }
    }
}
