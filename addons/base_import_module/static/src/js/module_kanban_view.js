/** @odoo-module **/

import { ModuleSearchModel } from "@base_import_module/js/search_model";
import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";

export const moduleKanbanView = {
    ...kanbanView,
    SearchModel: ModuleSearchModel,
};

registry.category("views").add("module_kanban", moduleKanbanView);
