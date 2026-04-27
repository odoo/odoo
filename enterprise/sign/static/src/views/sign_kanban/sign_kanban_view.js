/** @odoo-module **/

import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { SignKanbanController } from "@sign/views/sign_kanban/sign_kanban_controller";
import { SignKanbanRenderer } from "@sign/views/sign_kanban/sign_kanban_renderer";

export const signKanbanView = {
    ...kanbanView,
    Controller: SignKanbanController,
    Renderer: SignKanbanRenderer,
};
registry.category("views").add("sign_kanban", signKanbanView);
