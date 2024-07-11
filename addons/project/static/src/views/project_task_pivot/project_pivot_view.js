/** @odoo-module **/

import { ProjectControlPanel } from "@project/components/project_control_panel/project_control_panel";
import { registry } from "@web/core/registry";
import { pivotView } from "@web/views/pivot/pivot_view";
import { ProjectTaskPivotModel } from "./project_pivot_model";

const projectPivotView = {
    ...pivotView,
    ControlPanel: ProjectControlPanel,
    Model: ProjectTaskPivotModel,
};

registry.category("views").add("project_pivot", projectPivotView);
