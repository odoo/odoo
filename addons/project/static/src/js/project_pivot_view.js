/** @odoo-module **/

import { PivotView } from "@web/views/pivot/pivot_view";
import { ProjectControlPanel } from "@project/project_control_panel/project_control_panel";
import { registry } from "@web/core/registry";

const viewRegistry = registry.category("views");

class ProjectPivotView extends PivotView {}
ProjectPivotView.components = { ...PivotView, ControlPanel: ProjectControlPanel };
ProjectPivotView.ControlPanel = ProjectControlPanel; // TODO remove when JUM has merged his PR SearchPanel

viewRegistry.add("project_pivot", ProjectPivotView);
