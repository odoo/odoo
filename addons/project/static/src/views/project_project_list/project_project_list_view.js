import { registry } from "@web/core/registry";
import { listView } from '@web/views/list/list_view';
import { ProjectProjectListRenderer } from "./project_project_list_renderer";
import { ProjectListController } from "./project_project_list_controller";
import { ProjectRelationalModel } from "../project_relational_model";

export const projectProjectListView = {
    ...listView,
    Renderer: ProjectProjectListRenderer,
    Controller: ProjectListController,
    Model: ProjectRelationalModel,
};

registry.category("views").add("project_project_list", projectProjectListView);
