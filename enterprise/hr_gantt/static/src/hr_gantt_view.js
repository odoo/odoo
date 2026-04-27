import { ganttView } from "@web_gantt/gantt_view";
import { HrGanttRenderer } from "./hr_gantt_renderer";
import { registry } from "@web/core/registry";

const viewRegistry = registry.category("views");

export const hrGanttView = {
    ...ganttView,
    Renderer: HrGanttRenderer,
};

viewRegistry.add("hr_gantt", hrGanttView);
