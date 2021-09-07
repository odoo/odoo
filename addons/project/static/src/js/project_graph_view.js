/** @odoo-module **/

import { GraphView } from "@web/views/graph/graph_view";
import { ProjectControlPanel } from "@project/project_control_panel/project_control_panel";
import { registry } from "@web/core/registry";

const viewRegistry = registry.category("views");

class ProjectGraphView extends GraphView {}
ProjectGraphView.components = { ...GraphView, ControlPanel: ProjectControlPanel };

viewRegistry.add("project_graph", ProjectGraphView);
