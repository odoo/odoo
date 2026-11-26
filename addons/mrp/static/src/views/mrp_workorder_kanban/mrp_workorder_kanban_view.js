/** @odoo-module **/

import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { MrpWorkorderKanbanRenderer } from "./mrp_workorder_kanban_renderer";

export const mrpWorkorderKanbanView = {
    ...kanbanView,
    Renderer: MrpWorkorderKanbanRenderer,
};

registry.category("views").add("mrp_workorder_kanban", mrpWorkorderKanbanView);
