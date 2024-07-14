/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { markup, onMounted, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { escape } from "@web/core/utils/strings";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { AddressRecurrencyConfirmationDialog } from "@planning/components/address_recurrency_confirmation_dialog/address_recurrency_confirmation_dialog";

export class PlanningFormController extends FormController {
    setup() {
        super.setup();
        this.action = useService("action");
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.state = useState({
            recurrenceUpdate: "this",
        });
        onMounted(() => {
            this.initialTemplateCreation = this.model.root.data.template_creation;
        });
    }

    async saveButtonClicked(params = {}) {
        // In case this is the nth occurence,
        // and we update the number of occurences of the recurrency to < n,
        // ths occurence will be deleted. In that case, we need to go back to previous view.
        try {
            return await super.saveButtonClicked(params);
        } catch {
            this.env.config.historyBack()
        }
        return false;
    }

    async onRecordSaved(record, changes) {
        if ("repeat" in changes && record.data["repeat"]) {
            const message = _t("The recurring shifts have successfully been created.");
            this.notification.add(
                markup(
                    `<i class="fa fa-fw fa-check"></i><span class="ms-1">${escape(message)}</span>`
                ),
                { type: "success" }
            );
        }
    }

    async beforeExecuteActionButton(clickParams) {
        const shift = this.model.root;
        this.state.recurrenceUpdate = shift.data.recurrence_update;
        if (clickParams.name === "unlink") {
            const canProceed = await new Promise((resolve) => {
                if (shift.data.recurrency_id) {
                    this.dialogService.add(AddressRecurrencyConfirmationDialog, {
                        cancel: () => resolve(false),
                        close: () => resolve(false),
                        confirm: async () => {
                            await this._actionAddressRecurrency(shift);
                            return resolve(true);
                        },
                        onChangeRecurrenceUpdate: this._setRecurrenceUpdate.bind(this),
                        selected: this.state.recurrenceUpdate,
                    });
                } else {
                    this.dialogService.add(ConfirmationDialog, {
                        body: _t("Are you sure you want to delete this shift?"),
                        confirmLabel: _t("Delete"),
                        cancel: () => resolve(false),
                        close: () => resolve(false),
                        confirm: () => resolve(true),
                    });
                }
            });
            if (!canProceed) {
                return false;
            }
        } else if (clickParams.name === 'action_send' && shift.resId) {
            // We want to check if all employees impacted to this action have a email.
            // For those who do not have any email in work_email field, then a FormViewDialog is displayed for each employee who is not email.
            const result = await this.orm.call(this.props.resModel, "get_employees_without_work_email", [shift.resId]);
            if (result) {
                const { res_ids: resIds, relation: resModel, context } = result;
                const canProceed = await this.displayDialogWhenEmployeeNoEmail(resIds, resModel, context);
                if (!canProceed) {
                    return false;
                }
            }
        }
        if (!this.initialTemplateCreation && shift.data.template_creation) {
            // then the shift should be saved as a template too.
            const message = _t("This shift was successfully saved as a template.");
            this.notification.add(
                markup(`<i class="fa fa-fw fa-check"></i><span class="ms-1">${escape(message)}</span>`),
                { type: "success" },
            );
        }
        return super.beforeExecuteActionButton(clickParams);
    }

    /**
     * Display a dialog form view of employee model for each employee who has no work email.
     *
     * @param {Array<number>} resIds the employee ids without work email.
     * @param {string} resModel the model name to display the form view.
     * @param {Object} context context.
     *
     * @returns {Promise}
     */
    async displayDialogWhenEmployeeNoEmail(resIds, resModel, context) {
        const results = await Promise.all(resIds.map((resId) => {
            return new Promise((resolve) => {
                this.dialogService.add(FormViewDialog, {
                    title: "",
                    resModel,
                    resId,
                    context,
                    preventCreate: true,
                    onRecordSaved: () => resolve(true),
                }, { onClose: () => resolve(false) });
            });
        }));
        return results.every((r) => r);
    }

    async deleteRecord() {
        const shift = this.model.root;
        if (shift.data.recurrency_id) {
            this.dialogService.add(AddressRecurrencyConfirmationDialog, {
                confirm: async () => {
                    await this._actionAddressRecurrency(shift);
                    await shift.delete().then(
                        () => {
                            if (!shift.resId) {
                                this.env.config.historyBack();
                            }
                        },
                        () => {
                            this.env.config.historyBack();
                        }
                    );
                },
                onChangeRecurrenceUpdate: this._setRecurrenceUpdate.bind(this),
            });
        } else {
            await super.deleteRecord(...arguments);
        }
    }

    async _actionAddressRecurrency(shift) {
        if (['subsequent', 'all'].includes(this.state.recurrenceUpdate)) {
            await this.orm.call(
                shift.resModel,
                'action_address_recurrency',
                [shift.resId, this.state.recurrenceUpdate],
            );
        }
    }

    _setRecurrenceUpdate(recurrenceUpdate) {
        this.state.recurrenceUpdate = recurrenceUpdate;
    }
}

export const planningFormView = {
    ...formView,
    Controller: PlanningFormController,
};

registry.category("views").add("planning_form", planningFormView);
