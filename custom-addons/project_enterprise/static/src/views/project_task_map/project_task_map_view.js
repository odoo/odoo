/** @odoo-module **/

import { registry } from "@web/core/registry";
import { mapView } from "@web_map/map_view/map_view";
import { ProjectTaskMapModel } from "./project_task_map_model";
import { ProjectControlPanel } from "@project/components/project_control_panel/project_control_panel";

registry.category("views").add("project_task_map", {
    ...mapView,
    Model: ProjectTaskMapModel,
    ControlPanel: ProjectControlPanel
});
