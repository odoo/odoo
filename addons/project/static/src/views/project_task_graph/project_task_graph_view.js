import { graphView } from "@web/views/graph/graph_view";
import { ProjectTaskControlPanel } from "../project_task_control_panel/project_task_control_panel";
import { ProjectTaskGraphModel } from "./project_task_graph_model";
import { registry } from "@web/core/registry";

export const projectTaskGraphView = {
    ...graphView,
    ControlPanel: ProjectTaskControlPanel,
    Model: ProjectTaskGraphModel,
}

registry.category("views").add("project_task_graph", projectTaskGraphView);
