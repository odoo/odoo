/** @odoo-module **/

import { ProjectControlPanel } from "@project/components/project_control_panel/project_control_panel";
import { registry } from "@web/core/registry";
import { graphView } from "@web/views/graph/graph_view";

const viewRegistry = registry.category("views");

export const projectGraphView = {...graphView, ControlPanel: ProjectControlPanel};

viewRegistry.add("project_graph", projectGraphView);
