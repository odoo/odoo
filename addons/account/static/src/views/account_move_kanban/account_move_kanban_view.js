import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { AccountMoveKanbanController } from "./account_move_kanban_controller";

export const accountMoveUploadKanbanView = {
    ...kanbanView,
    Controller: AccountMoveKanbanController,
};

registry.category("views").add("account_documents_kanban", accountMoveUploadKanbanView);
