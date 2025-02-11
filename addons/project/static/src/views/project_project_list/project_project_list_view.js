/** @odoo-module */

import { registry } from "@web/core/registry";
import { listView } from '@web/views/list/list_view';
import { ProjectProjectListRenderer } from "./project_project_list_renderer";

export const projectProjectListView = {
    ...listView,
    Renderer: ProjectProjectListRenderer,
};

registry.category("views").add("project_project_list", projectProjectListView);
