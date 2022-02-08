/** @odoo-module **/

import { ProjectControlPanel } from "@project/project_control_panel/project_control_panel";
import { registry } from "@web/core/registry";
import { GraphView } from "@web/views/graph/graph_view";

const viewRegistry = registry.category("views");

export class ProjectGraphView extends GraphView {}
ProjectGraphView.ControlPanel = ProjectControlPanel;

viewRegistry.add("project_graph", ProjectGraphView);
