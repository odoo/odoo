/* @odoo-module */

import { ganttView } from "@web_gantt/gantt_view";
import { registry } from "@web/core/registry";
import { WorkEntriesGanttController } from "./work_entries_gantt_controller";
import { WorkEntriesGanttModel } from "./work_entries_gantt_model";

const viewRegistry = registry.category("views");

export const workEntriesGanttView = {
    ...(viewRegistry.content.hr_gantt?.[1] ?? ganttView),
    Controller: WorkEntriesGanttController,
    Model: WorkEntriesGanttModel,
    buttonTemplate: "hr_work_entry_contract_enterprise.WorkEntriesGanttView.Buttons",
};

viewRegistry.add("work_entries_gantt", workEntriesGanttView);

// hr_gantt should normally be installed unless manually removed,
// so "stable" workaround to leave dependencies unchanged
function updateWorkEntriesGanttView(evt) {
    const { operation, key, value } = evt.detail;
    if (key === "hr_gantt" && operation === "add") {
        Object.assign(workEntriesGanttView, {
            ...value,
            Controller: WorkEntriesGanttController,
            Model: WorkEntriesGanttModel,
            buttonTemplate: "hr_work_entry_contract_enterprise.WorkEntriesGanttView.Buttons",
        });
        viewRegistry.removeEventListener("UPDATE", updateWorkEntriesGanttView);
    }
}

if (!viewRegistry.content.hr_gantt) {
    viewRegistry.addEventListener("UPDATE", updateWorkEntriesGanttView);
}
