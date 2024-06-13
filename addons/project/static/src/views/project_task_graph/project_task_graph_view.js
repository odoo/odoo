/** @odoo-module **/

import { registry } from "@web/core/registry";
import { graphView } from "@web/views/graph/graph_view";
import { ProjectTaskGraphModel } from "./project_task_graph_model";

const viewRegistry = registry.category("views");

export const projectTaskGraphView = {
    ...graphView,
    Model: ProjectTaskGraphModel,
};

viewRegistry.add("project_task_graph", projectTaskGraphView);
