import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { serializeDate } from "@web/core/l10n/dates";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";
import { FormRenderer } from "@web/views/form/form_renderer";
import { ContractEndDialog } from "@hr/components/contract_end_dialog/contract_end_dialog";
import { VersionUpdateDialog } from "@hr/components/version_update_dialog/version_update_dialog";

export class EmployeeFormController extends FormController {
    setup() {
        super.setup();
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
        this.pendingNewContract = null;
    }

    /**
     * Return a dialog asking how the version updates are applied
     */
    _getVersionUpdateDialogClass(_record) {
        return VersionUpdateDialog;
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
        const versionId = record._values.version_id?.id;
        if (!record.resId || record.resModel !== "hr.employee" || !versionId) {
            return true;
        }
        const versionChanges = Object.fromEntries(
            Object.entries(changes).filter(([fieldName]) =>
                record.fields[fieldName]?.related?.startsWith("version_id.")
            )
        );
        if (!Object.keys(versionChanges).length) {
            return true;
        }

        const update_info = await this.orm.call("hr.version", "get_version_update_info", [
            [versionId],
            versionChanges,
        ]);
        if (!update_info) {
            return true;
        }

        let choice = null;
        while (true) {
            choice = await new Promise((resolve) => {
                this.dialogService.add(
                    this._getVersionUpdateDialogClass(record),
                    { info: update_info, record, changes, defaultChoice: choice, confirm: resolve },
                    { onClose: () => resolve(null) }
                );
            });
            if (!choice) {
                return false;
            }
            const canSave = await this._applyVersionUpdateChoice(
                record,
                changes,
                versionId,
                update_info,
                choice
            );
            // null: the choice was cancelled, ask again
            if (canSave !== null) {
                return canSave;
            }
        }
    }

    async _applyVersionUpdateChoice(record, changes, versionId, updateInfo, choice) {
        switch (choice.mode) {
            // write the updates on the current version only
            case "current":
                return true;

            // write the updates on the current version & the next versions also
            case "next_versions":
                await this.orm.write(
                    "hr.version",
                    [versionId, ...updateInfo.next_version_ids],
                    updateInfo.version_changes
                );
                // already written: the save must not write them again
                for (const fieldName of Object.keys(updateInfo.version_changes)) {
                    delete changes[fieldName];
                }
                return true;

            // create new version with the updates
            case "new_version":
                await this.orm.call("hr.version", "action_create_version_from_update", [
                    [versionId],
                    choice.date,
                    updateInfo.version_changes,
                ]);
                await this.model.load();
                return false;
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
