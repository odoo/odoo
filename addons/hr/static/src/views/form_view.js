import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { serializeDate } from "@web/core/l10n/dates";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";
import { FormRenderer } from "@web/views/form/form_renderer";
import { ContractEndDialog } from "@hr/components/contract_end_dialog/contract_end_dialog";

export class EmployeeFormController extends FormController {
    setup() {
        super.setup();
        this.dialogService = useService("dialog");
        this.pendingNewContract = null;
    }

    get modelParams() {
        const params = super.modelParams;
        params.hooks.onRecordChanged = this.onRecordChanged.bind(this);
        return params;
    }

    /**
     * Called on the client side every time the record is updated (i.e. every
     * time a field value changes), not only on save. `changes` holds the
     * record's current pending diff, so we only act when contract_date_end
     * is actually part of it.
     */
    async onRecordChanged(record, changes) {
        if (!("contract_date_end" in changes)) {
            return;
        }

        const contractDateStart = record.data.contract_date_start;
        const contractDateEnd = record.data.contract_date_end;
        const previousContractDateStart = record._values?.contract_date_start;
        const previousContractDateEnd = record._values?.contract_date_end;
        const hasDeparture = record.data.departure_id;

        if (
            previousContractDateStart !== contractDateStart
            || previousContractDateEnd === contractDateEnd
            || !contractDateEnd
            || hasDeparture
            || record._skipContractEndDialog
        ) {
            return;
        }

        return new Promise((resolve) => {
            this.dialogService.add(ContractEndDialog, {
                record: record,
            }, {
                onClose: (result) => {
                    // Resolve immediately so the *current* record.update() call
                    // (the one that triggered this onRecordChanged) can unwind.
                    // Any follow-up mutation on the record must happen afterwards,
                    // as a separate update() call, or it gets silently dropped
                    // because the record doesn't support reentrant updates.
                    resolve();
                    setTimeout(() => {
                        this._applyContractEndDialogResult(record, result, {
                            contractDateEnd,
                            previousContractDateEnd,
                        });
                    }, 0);
                },
            });
        });
    }

    async _applyContractEndDialogResult(record, result, { contractDateEnd, previousContractDateEnd }) {
        switch (result?.reason) {
            case "correction":
                await record.update({ fixed_term: true });
                break;
            case "end_collaboration":
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
            default: {
                // Revert to the last saved value. This makes contract_date_end
                // match previousContractDateEnd again, so the guard in
                // onRecordChanged short-circuits on the re-entrant call this
                // triggers, and the dialog won't reopen.
                await record.update({
                    contract_date_end: previousContractDateEnd || false,
                });
                break;
            }
        }
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
}

export class EmployeeFormRenderer extends FormRenderer {}

registry.category("views").add("hr_employee_form", {
    ...formView,
    Controller: EmployeeFormController,
    Renderer: EmployeeFormRenderer,
});
