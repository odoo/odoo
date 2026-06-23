import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

class WorkingScheduleDialog extends Component {
    static template = "resource.WorkingScheduleDialog";
    static props = {
        employeeCount: Number,
        confirmUpdate: Function,
        createNew: Function,
        cancel: Function,
        close: Function,
    };
}

export class ResourceCalendarController extends formView.Controller {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.actionService = useService("action");
        this.orm = useService("orm");

        this.forceSave = false;
        this.isCustomFlow = false;
        this.deferredChangesResolve = null;
    }

    /**
     * @override
     * Catch the changes payload right before sending it to the backend.
     */
    async onWillSaveRecord(record, changes) {
        await super.onWillSaveRecord(...arguments);

        // If our custom interceptor dialog is running, route the changes back to it
        if (this.isCustomFlow && this.deferredChangesResolve) {
            this.deferredChangesResolve(changes);
            this.deferredChangesResolve = null;
            return false;
        }

        return true;
    }

    /**
     * @override
     */
    async saveButtonClicked(params = {}) {
        const record = this.model.root;
        const employeeCount = record.data.employees_count || 0;

        if (this.forceSave || employeeCount <= 1) {
            this.forceSave = false;
            this.isCustomFlow = false;
            return super.saveButtonClicked(params);
        }

        this.isCustomFlow = true;

        // Promise that will resolve with the changes payload, when super.save() triggers onWillSaveRecord.
        const changesPromise = new Promise((r) => {
            this.deferredChangesResolve = r;
        });

        // Trigger super.save() quietly to force the UI components to flush and validate the values
        // Pass a dummy error handler so the browser doesn't trace an unhandled rejection.
        this.save({ onError: () => {} });

        const changes = await changesPromise;

        return new Promise((resolve) => {
            const popup_dialog = this.dialog.add(WorkingScheduleDialog, {
                employeeCount,

                confirmUpdate: async () => {
                    this.forceSave = true;
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
                    this.forceSave = false;
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
    Controller: ResourceCalendarController,
});
