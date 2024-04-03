/** @odoo-module **/

import { registry } from "@web/core/registry";

import { kanbanView } from "@web/views/kanban/kanban_view";
import { MrpDocumentsKanbanController } from "@mrp/views/mrp_documents_kanban/mrp_documents_kanban_controller";
import { MrpDocumentsKanbanRenderer } from "@mrp/views/mrp_documents_kanban/mrp_documents_kanban_renderer";

export const mrpDocumentsKanbanView = {
    ...kanbanView,
    Controller: MrpDocumentsKanbanController,
    Renderer: MrpDocumentsKanbanRenderer,
    buttonTemplate: "mrp.MrpDocumentsKanbanView.Buttons",
};

registry.category("views").add("mrp_documents_kanban", mrpDocumentsKanbanView);
