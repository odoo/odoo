import { ProjectTaskControlPanel } from "../project_task_control_panel/project_task_control_panel";
import { registry } from "@web/core/registry";
import { ProjectTaskPivotModel } from "./project_task_pivot_model";
import { pivotView } from "@web/views/pivot/pivot_view";

export const projectTaskPivotView = {
    ...pivotView,
    ControlPanel: ProjectTaskControlPanel,
    Model: ProjectTaskPivotModel,
}

registry.category("views").add("project_task_pivot", projectTaskPivotView);
