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
        this.action = useService("action");
        this.orm = useService("orm");

        this.forceSave = false;
    }

    async saveButtonClicked(params = {}) {
        const record = this.model.root;
        const employeeCount = record.data.employees_count || 0;

        if (this.forceSave || employeeCount <= 1) {
            this.forceSave = false;
            return super.saveButtonClicked(params);
        }

        return new Promise((resolve) => {
            const popup_dialog = this.dialog.add(WorkingScheduleDialog, {
                employeeCount,

                confirmUpdate: async () => {
                    this.forceSave = true;
                    popup_dialog();

                    const result = await super.saveButtonClicked(params);
                    resolve(result);
                },

                cancel: () => {
                    popup_dialog();
                    resolve(false);
                },

                createNew: async () => {
                    this.forceSave = false;
                    popup_dialog();

                    await record.discard();

                    const newId = await this.orm.call(
                        "resource.calendar",
                        "create_calendar_copy",
                        [
                            record.resId
                        ]
                    );

                    await this.action.doAction({
                        type: "ir.actions.act_window",
                        res_model: "resource.calendar",
                        res_id: newId,
                        views: [[false, "form"]],
                        target: "current",
                    });
                    resolve(false);
                },
            });
        });
    }
}

registry.category("views").add("resource_calendar_form", {
    ...formView,
    Controller: ResourceCalendarController,
});
