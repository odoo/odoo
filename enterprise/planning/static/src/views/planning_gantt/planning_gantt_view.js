import { registry } from "@web/core/registry";
import { ganttView } from "@web_gantt/gantt_view";
import { PlanningGanttController } from "./planning_gantt_controller";
import { PlanningGanttModel } from "./planning_gantt_model";
import { PlanningGanttRenderer } from "./planning_gantt_renderer";
import { PlanningSearchModel } from "../planning_search_model";

const viewRegistry = registry.category("views");

export const PlanningGanttView = {
    ...ganttView,
    SearchModel: PlanningSearchModel,
    Controller: PlanningGanttController,
    Renderer: PlanningGanttRenderer,
    Model: PlanningGanttModel,
    buttonTemplate: "planning.PlanningGanttView.Buttons",
};

viewRegistry.add("planning_gantt", PlanningGanttView);
