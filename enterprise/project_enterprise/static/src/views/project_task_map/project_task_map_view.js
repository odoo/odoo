/** @odoo-module **/

import { registry } from "@web/core/registry";
import { mapView } from "@web_map/map_view/map_view";
import { ProjectTaskMapModel } from "./project_task_map_model";
import { ProjectTaskMapRenderer } from "./project_task_map_renderer";
import { HighlightProjectTaskSearchModel } from "../highlight_project_task_search_model";

export const projectTaskMapView = {
    ...mapView,
    Model: ProjectTaskMapModel,
    Renderer: ProjectTaskMapRenderer,
    SearchModel: HighlightProjectTaskSearchModel,
};

registry.category("views").add("project_task_map", projectTaskMapView);
