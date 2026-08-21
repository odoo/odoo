/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";


export class ResourceCalendarWarningDialog extends Component {
    static template = "hr.ResourceCalendarWarningDialog";
    static components = { Dialog };
    static props = {
        employeesCount: Number,
        confirmUpdate: Function,
        createNew: Function,
        cancel: Function,
    };
}

export class ResourceCalendarFormController extends FormController {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.actionService = useService("action");
        this.orm = useService("orm");

        this.isCustomFlow = false;
        this.deferredChangesResolve = null;
    }

    async onWillSaveRecord(record, changes) {
        await super.onWillSaveRecord(...arguments);

        // When custom flow is active, transfer the pending changes payload back to the 
        // waiting saveButtonClicked Promise and prevent the standard database write
        if (this.isCustomFlow && this.deferredChangesResolve) {
            this.deferredChangesResolve(changes);
            this.deferredChangesResolve = null;
            return false;
        }

        return true; // Allows the standard save
    }

    async saveButtonClicked(params = {}) {
        const record = this.model.root;
        const employeesCount = record.data.employees_count || 0;

        if (employeesCount <= 1) {
            this.isCustomFlow = false;
            return super.saveButtonClicked(params);
        }

        this.isCustomFlow = true;

        const changesPromise = new Promise((r) => {
            this.deferredChangesResolve = r;
        });

        // Trigger save() to flush UI inputs and force field validation.
        // Catch and ignore the expected cancellation errors caused by returning False in onWillSaveRecord().
        this.save({ onError: () => {} });

        const changes = await changesPromise;

        return new Promise((resolve) => {
            const popup_dialog = this.dialog.add(ResourceCalendarWarningDialog, {
                employeesCount,

                confirmUpdate: async () => {
                    this.isCustomFlow = false;
                    popup_dialog();

                    const result = await super.saveButtonClicked(params);
                    resolve(result);
                },

                cancel: async () => {
                    this.isCustomFlow = false;
                    popup_dialog();

                    await this.discard();
                    resolve(false);
                },

                createNew: async () => {
                    this.isCustomFlow = false;
                    popup_dialog();

                    await this.discard();

                    const newId = await this.orm.call(
                        "resource.calendar",
                        "create_calendar_copy_with_updates",
                        [
                            record.resId,
                            changes,
                        ]
                    );

                    resolve(false);

                    await this.actionService.doAction({
                        type: "ir.actions.act_window",
                        res_model: "resource.calendar",
                        res_id: newId,
                        views: [[false, "form"]],
                        target: "current",
                    });
                },
            });
        });
    }
}

registry.category("views").add("resource_calendar_form", {
    ...formView,
    Controller: ResourceCalendarFormController,
});
