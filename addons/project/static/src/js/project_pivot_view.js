/** @odoo-module **/

import { ProjectControlPanel } from "@project/project_control_panel/project_control_panel";
import { registry } from "@web/core/registry";
import { PivotView } from "@web/views/pivot/pivot_view";

const viewRegistry = registry.category("views");

class ProjectPivotView extends PivotView {}
ProjectPivotView.ControlPanel = ProjectControlPanel;

viewRegistry.add("project_pivot", ProjectPivotView);
