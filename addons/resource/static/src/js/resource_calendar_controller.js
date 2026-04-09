import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";

class WorkingScheduleDialog extends Component {
    static template = "my_module.WorkingScheduleDialog";
    static props = {
        workResourcesCount: Number,
        confirmUpdate: Function,
        createNew: Function,
        cancel: Function,
        close: Function,
    };
}

export class ResourceCalendarController extends formView.Controller {
    setup() {
        console.log(">> ResourceCalendarController setup");
        super.setup();
        this.dialog = useService("dialog");
        this.action = useService("action");
        this.orm = useService("orm");

        this.forceSave = false;
    }

    normalizeValues(changes) {
        const normalized = { ...changes };
        console.log(">> normalizeValues", normalized);

        for (const [field, value] of Object.entries(changes)) {
            if (Array.isArray(value)) {
                normalized[field] = value.map(cmd => {
                    const [type, id, data] = cmd;

                    if (type === 0) return cmd;

                    if (type === 1 || type === 2) {
                        return cmd;
                    }
                    if (type === 6) return cmd;
                    return cmd;
                });
            }

            if (value && typeof value === "object" && "id" in value) {
                normalized[field] = value.id;
            }
        }

        return normalized;
    }

    async onRecordSaved(record) {
        console.log(">> onRecordSaved");
        await super.onRecordSaved(...arguments);
    }

    async onWillSaveRecord(record, changes) {
        console.log(">> onWillSaveRecord");
        //const res = await super.onWillSaveRecord(...arguments);
        //debugger;

        if (this.forceSave) {
            this.forceSave = false;
            return true;
        }

        const workResourcesCount = record.data.work_resources_count || 0;

        // no warning needed
        if (workResourcesCount <= 1) {
            return true;
        }

        return new Promise((resolve) => {
            const dialog = this.dialog.add(WorkingScheduleDialog, {
                workResourcesCount,

                confirmUpdate: () => {
                    this.forceSave = true;
                    dialog();
                    resolve(true);
                },

                cancel: () => {
                    record.model.root.discard();
                    dialog();
                    resolve(false);
                },

                createNew: async () => {
                    //console.log("ENTER createNew");

                    const currentId = record.resId;

                    // 3. Now it is safe to revert UI changes on the original record
                    record.model.root.discard();
                    record.discard();
                    dialog();
                    resolve(false);


                    

                    //console.log(">> createNew with changes", changes);

                    // 2. Call Copy 'This call cause the values to be recomputed in cache and the copy to be created with the new values. 
                    // The original record is still unchanged in the database at this point
                    // , but The cache of the form is now in a "dirty" state with the changes applied on top of the original record 
                    // (which is what we want because we want the copy to be created with these changes). 
                    // , also The copy is created but not yet updated with the changes.'
                    const newIds = await this.orm.call(
                        "resource.calendar",
                        "copy",
                        [[currentId]],
                        { default: changes }
                    );
                    const newId = Array.isArray(newIds) ? newIds[0] : newIds;

                    //console.log(">> newId", newId);

                    // We use 'write' because it perfectly handles the Command arrays from getChanges()
                    //if (Object.keys(changes).length > 0) {
                    //    await this.orm.write("resource.calendar", [newId], changes);
                    //}

                    // 3. Call Write to apply the changes on the copy (which is now a separate record with its own cache)
                    //await this.orm.write("resource.calendar", [newId], changes);

                    

                    // 4. Link to employee if navigated from one
                    const context = record.context || {};
                    if (context.active_model === "hr.employee" && context.active_id) {
                        await this.orm.write("hr.employee", [parseInt(context.active_id)], {
                            resource_calendar_id: newId,
                        });
                    }



                    // 5. Redirect to the new record
                    await this.action.doAction({
                        type: "ir.actions.act_window",
                        res_model: "resource.calendar",
                        res_id: newId,
                        views: [[false, "form"]],
                        target: "current",
                    });
                },
            });
        });
        //return res;
        return true;
    }
}

registry.category("views").add("resource_calendar_form", {
    ...formView,
    Controller: ResourceCalendarController,
});
