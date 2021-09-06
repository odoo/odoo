/** @odoo-module **/

import { PivotView } from "@web/views/pivot/pivot_view";
import { ProjectControlPanel } from "@project/project_control_panel/project_control_panel";
import { registry } from "@web/core/registry";

const viewRegistry = registry.category("views");

class ProjectPivotView extends PivotView {}
ProjectPivotView.components = { ...PivotView.components, ControlPanel: ProjectControlPanel };

viewRegistry.add("project_pivot", ProjectPivotView);
