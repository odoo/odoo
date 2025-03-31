/** @odoo-module **/

import { registry } from "@web/core/registry";
import { pivotView } from "@web/views/pivot/pivot_view";
import { ProjectTaskPivotModel } from "./project_pivot_model";

export const projectPivotView = {
    ...pivotView,
    Model: ProjectTaskPivotModel,
};

registry.category("views").add("project_pivot", projectPivotView);
