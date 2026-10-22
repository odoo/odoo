import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { serializeDate } from "@web/core/l10n/dates";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";
import { FormRenderer } from "@web/views/form/form_renderer";
import { ContractEndDialog } from "@hr/components/contract_end_dialog/contract_end_dialog";
import { MultiVersionUpdateConfirmationDialog } from "./form/multi_version_update_confirmation_dialog";

export class EmployeeFormController extends FormController {
    setup() {
        super.setup();
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
        this.pendingNewContract = null;
    }

    _getVersionUpdateDialogClass(_record) {
        return MultiVersionUpdateConfirmationDialog;
    }

    async onRecordChanged(record, changes) {
        super.onRecordChanged(...arguments);
        if (!("contract_date_end" in changes)) {
            return;
        }
        const contractDateEnd = record.data.contract_date_end;
        const previousContractDateEnd = record._values?.contract_date_end;
        const bypassContractEndDialog =
            // a new contract is being encoded: its end date is not a change of the current contract
            record._values?.contract_date_start !== record.data.contract_date_start ||
            previousContractDateEnd === contractDateEnd ||
            !contractDateEnd ||
            record.data.departure_id ||
            record._skipContractEndDialog;
        if (bypassContractEndDialog) {
            return;
        }
        // Ask as soon as the end date is changed, without waiting for the save (autosave would be
        // blocked by the dialog). The result is applied once this hook returns, as it updates and
        // saves the record.
        const result = await new Promise((resolve) => {
            this.dialogService.add(ContractEndDialog, { record }, { onClose: resolve });
        });
        setTimeout(() =>
            this._applyContractEndDialogResult(record, result, previousContractDateEnd)
        );
    }

    async onWillSaveRecord(record, changes) {
        // Only run the logic if it's not an employee creation but an update
        // and if it's only directly on the employee form not in a popup for another model
        if (Boolean(record._config.resId) && record._config.resModel == "hr.employee") {
            // We extract the versions of the employee so that we can check if we're on the last one chronologically
            let ver_ids = await this.orm.read("hr.employee", [record.resId], ["version_ids"]);
            ver_ids = ver_ids[0].version_ids;

            // We need to differentiate the fields that are related to the version from those that are only related to the employee, also the contract date limits should never be copied to different versions
            const version_changes = Object.fromEntries(
                Object.entries(changes).filter(
                    ([key]) =>
                        record.fields[key].related?.includes("version_id") &&
                        !["contract_date_start", "contract_date_end"].includes(
                            record.fields[key].name
                        )
                )
            );

            // If we have version-related changes and we are not on the last version
            if (
                Object.keys(version_changes).length > 0 &&
                record._values.version_id.id !== ver_ids.at(-1)
            ) {
                const version_changes_to_display = await this.orm.call(
                    "hr.employee",
                    "get_multi_version_changes",
                    [record.resId],
                    {
                        version_changes: version_changes,
                    }
                );
                const proceed = await new Promise((resolve) => {
                    this.dialogService.add(
                        this._getVersionUpdateDialogClass(record),
                        {
                            title: "Apply changes to next versions?",
                            version_changes: version_changes_to_display,
                            record,
                            changes,
                            cancel: () => resolve(false),
                            change_current: () => resolve(true),
                            change_multi: async () => {
                                const versions_to_update = ver_ids.slice(
                                    ver_ids.indexOf(record._values.version_id.id)
                                );
                                await this.orm.write(
                                    "hr.version",
                                    versions_to_update,
                                    version_changes
                                );
                                // Already written and tracked on all the versions, don't write them again on save
                                for (const fieldName of Object.keys(version_changes)) {
                                    delete changes[fieldName];
                                }
                                resolve(true);
                            },
                        },
                        {
                            onClose: () => resolve(false),
                        }
                    );
                });
                if (!proceed) {
                    return false;
                }
            }
        }
        return true;
    }

    async onRecordSaved(record, changes) {
        await super.onRecordSaved(record, changes);

        if (this.pendingNewContract) {
            const version_id = await this.orm.call("hr.employee", "create_version", [
                record.resId,
                this.pendingNewContract,
            ]);
            this.pendingNewContract = null;

            await record.model.load({
                context: {
                    ...record.model.env.searchModel.context,
                    version_id,
                },
            });
        }
    }

    async _applyContractEndDialogResult(record, result, previousContractDateEnd) {
        record._skipContractEndDialog = true;
        try {
            if (!result?.reason || result.reason === "discard") {
                await record.update({ contract_date_end: previousContractDateEnd || false });
                return;
            }
            // the end date may have been corrected in the dialog
            const contractDateEnd = result.date || record.data.contract_date_end;
            await record.update({
                contract_date_end: contractDateEnd,
                ...(result.reason === "correction" ? { fixed_term: true } : {}),
            });
            if (result.reason === "new_contract") {
                const newContractDateStart = contractDateEnd.plus({ days: 1 });
                const newContractDateEnd =
                    previousContractDateEnd && contractDateEnd < previousContractDateEnd
                        ? previousContractDateEnd
                        : false;
                this.pendingNewContract = {
                    date_version: serializeDate(newContractDateStart),
                    contract_date_start: serializeDate(newContractDateStart),
                    contract_date_end: newContractDateEnd
                        ? serializeDate(newContractDateEnd)
                        : false,
                    contract_template_id: result.contractTemplateId,
                };
            }
            await record.save();
            if (result.reason === "end_collaboration") {
                this.actionService.doAction(result.action, {
                    onClose: async () => {
                        await record.model.load();
                    },
                });
            }
        } finally {
            record._skipContractEndDialog = false;
        }
    }
}

export class EmployeeFormRenderer extends FormRenderer {}

registry.category("views").add("hr_employee_form", {
    ...formView,
    Controller: EmployeeFormController,
    Renderer: EmployeeFormRenderer,
});
