/** @odoo-module **/

import { ProjectControlPanel } from "@project/components/project_control_panel/project_control_panel";
import { registry } from "@web/core/registry";
import { pivotView } from "@web/views/pivot/pivot_view";

const projectPivotView = {...pivotView, ControlPanel: ProjectControlPanel};

registry.category("views").add("project_pivot", projectPivotView);
