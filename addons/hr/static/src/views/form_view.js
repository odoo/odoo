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
        this.actionService = useService("action");
        this.orm = useService('orm');
        this.pendingNewContract = null;
    }

    get modelParams() {
        const params = super.modelParams;
        params.hooks.onRecordChanged = this.onRecordChanged.bind(this);
        return params;
    }

    async onRecordChanged(record, changes){
        if (!("contract_date_end" in changes)) {
            return;
        }
        const contractDateEnd = record.data.contract_date_end;
        const previousContractDateEnd = record._values?.contract_date_end;
        const hasDeparture = record.data.departure_id;

        const bypassContractEndDialog =
            previousContractDateEnd === contractDateEnd
            || !contractDateEnd
            || hasDeparture
            || record._skipContractEndDialog;

        if (!bypassContractEndDialog) {
            return new Promise((resolve) => {
                this.dialogService.add(ContractEndDialog, {
                    record: record,
                }, {
                    onClose: (result) => {
                        resolve();
                        setTimeout(() => {this._applyContractEndDialogResult(record, result, {
                                                contractDateEnd,
                                                previousContractDateEnd,
                        });
                        }, 0);  
                    },
                });
            });
        }
    }

    async onWillSaveRecord(record, changes) {
        // Only run the logic if it's not an employee creation but an update
        if (Boolean(record._config.resId)) {
            // We extract the versions of the employee so that we can check if we're on the last one chronologically
            let ver_ids = await this.orm.read('hr.employee', [record._values.employee_id.id], ['version_ids']);
            ver_ids = ver_ids[0].version_ids;

            // We need to differentiate the fields that are related to the version from those that are only related to the employee, also the contract date limits should never be copied to different versions
            const version_changes = Object.fromEntries(
                Object.entries(changes).filter(([key]) => (record.fields[key].related?.includes('version_id') && !(['contract_date_start', 'contract_date_end'].includes(record.fields[key].name))))
            );

            // If we have version-related changes and we are not on the last version
            if ((Object.keys(version_changes).length > 0) && record._values.version_id.id !== ver_ids.at(-1)) {

                let version_changes_to_display = await this.orm.call("hr.employee",
                    "get_multi_version_changes",
                    [record._config.resId],
                    {
                        'version_changes': version_changes,
                    }
                )
                const proceed = await new Promise((resolve) => {
                    this.dialogService.add(MultiVersionUpdateConfirmationDialog, {
                        title: "Apply changes to next versions?",
                        version_changes: version_changes_to_display,
                        cancel: () => resolve(false),
                        change_current: () => resolve(true),
                        change_multi: async () => {
                            let versions_to_update = ver_ids.slice(ver_ids.indexOf(record._values.version_id.id))
                            await this.orm.call("hr.version", "write", [versions_to_update.slice(1), version_changes]);
                            this.model._updateConfig(record.config, {
                                context: {
                                    ...record.config.context,
                                    multi_update_version_ids: versions_to_update,
                                },
                            }, { reload: false });
                            resolve(true);
                        },
                    }, {
                        onClose: () => resolve(false),
                    });
                });
                if (!proceed) return false;
            }
        }
        return true;
    }

    async onRecordSaved(record, changes) {
        await super.onRecordSaved(record, changes);
        if (record.config?.context?.multi_update_version_ids) {
            record.model._updateConfig(record.config, {
                context: Object.fromEntries(
                    Object.entries(record.config.context).filter(([key]) => key !== "multi_update_version_ids")
                ),
            }, { reload: false });
        }

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

    async _applyContractEndDialogResult(record, result, { contractDateEnd, previousContractDateEnd }) {
        record._skipContractEndDialog = true;
        try {
            switch (result?.reason) {
                case "correction":
                    await record.update({ fixed_term: true });
                    break;
                case "end_collaboration":
                    await record.update({ contract_date_end: contractDateEnd});
                    await record.save();
                    this.actionService.doAction(result.action, {
                        onClose: async () => {
                            await record.model.load();
                        },
                    });
                    break;
                case "new_contract": {
                    const newContractDateStart = contractDateEnd.plus({ days: 1 });
                    let newContractDateEnd = false;
                    if (previousContractDateEnd && contractDateEnd < previousContractDateEnd) {
                        newContractDateEnd = previousContractDateEnd;
                    }
                    this.pendingNewContract = {
                        date_version: serializeDate(newContractDateStart),
                        contract_date_start: serializeDate(newContractDateStart),
                        contract_date_end: newContractDateEnd ? serializeDate(newContractDateEnd) : false,
                        contract_template_id: result.contractTemplateId,
                    };
                    break;
                }
                case "discard":
                default:
                    await record.update({
                        contract_date_end: previousContractDateEnd || false,
                    });
                    break;
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
