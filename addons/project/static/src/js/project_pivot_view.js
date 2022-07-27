/** @odoo-module **/

import { ProjectControlPanel } from "@project/project_control_panel/project_control_panel";
import { registry } from "@web/core/registry";
import { pivotView } from "@web/views/pivot/pivot_view";

export const projectPivotView = pivotView.extend({
    config: {
        ...pivotView.prototype.config,
        ControlPanel: ProjectControlPanel,
    },
});

registry.category("views").add("project_pivot", projectPivotView);
