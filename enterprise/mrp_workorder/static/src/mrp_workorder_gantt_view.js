import { ganttView } from "@web_gantt/gantt_view";
import { MRPWorkorderGanttRenderer } from "./mrp_workorder_gantt_renderer";
import { registry } from "@web/core/registry";

const viewRegistry = registry.category("views");

export const mrpWorkorderGanttView = {
    ...ganttView,
    Renderer: MRPWorkorderGanttRenderer,
};

viewRegistry.add("mrp_workorder_gantt", mrpWorkorderGanttView);
