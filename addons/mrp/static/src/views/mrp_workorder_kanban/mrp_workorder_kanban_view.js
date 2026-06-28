/** @odoo-module **/

import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { MrpWorkorderKanbanController } from "./mrp_workorder_kanban_controller";
import { MrpWorkorderKanbanRenderer } from "./mrp_workorder_kanban_renderer";

export const mrpWorkorderKanbanView = {
    ...kanbanView,
    Controller: MrpWorkorderKanbanController,
    Renderer: MrpWorkorderKanbanRenderer,
    buttonTemplate: "mrp.MrpWorkorderKanbanController.Buttons",
};

registry.category("views").add("mrp_workorder_kanban", mrpWorkorderKanbanView);
