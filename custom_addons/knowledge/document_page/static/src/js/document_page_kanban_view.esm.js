import {DocumentPageKanbanController} from "./document_page_kanban_controller.esm";
import {kanbanView} from "@web/views/kanban/kanban_view";
import {registry} from "@web/core/registry";

export const documentPageKanbanView = {
    ...kanbanView,
    Controller: DocumentPageKanbanController,
};

registry.category("views").add("document_page_kanban_view", documentPageKanbanView);
