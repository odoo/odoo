/** @odoo-module **/

import { ProjectControlPanel } from "@project/components/project_control_panel/project_control_panel";
import { registry } from "@web/core/registry";
import { graphView } from "@web/views/graph/graph_view";
import { ProjectTaskGraphModel } from "./project_task_graph_model";

const viewRegistry = registry.category("views");

export const projectTaskGraphView = {
    ...graphView,
    ControlPanel: ProjectControlPanel,
    Model: ProjectTaskGraphModel,
};

viewRegistry.add("project_task_graph", projectTaskGraphView);
