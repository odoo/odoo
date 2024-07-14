/* @odoo-module */

import { ganttView } from "@web_gantt/gantt_view";
import { MRPWorkorderGanttModel } from "./mrp_workorder_gantt_model";
import { MRPWorkorderGanttRenderer } from "./mrp_workorder_gantt_renderer";
import { registry } from "@web/core/registry";

const viewRegistry = registry.category("views");

export const mrpWorkorderGanttView = {
    ...ganttView,
    Model: MRPWorkorderGanttModel,
    Renderer: MRPWorkorderGanttRenderer,
};

viewRegistry.add("mrp_workorder_gantt", mrpWorkorderGanttView);
