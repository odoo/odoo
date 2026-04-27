import { hrGanttView } from "@hr_gantt/hr_gantt_view";
import { registry } from "@web/core/registry";
import { WorkEntriesGanttController } from "./work_entries_gantt_controller";
import { WorkEntriesGanttModel } from "./work_entries_gantt_model";

const viewRegistry = registry.category("views");

export const workEntriesGanttView = {
    ...hrGanttView,
    Controller: WorkEntriesGanttController,
    Model: WorkEntriesGanttModel,
    buttonTemplate: "hr_work_entry_contract_enterprise.WorkEntriesGanttView.Buttons",
};

viewRegistry.add("work_entries_gantt", workEntriesGanttView);
