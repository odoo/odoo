import { registry } from "@web/core/registry";
import { fileUploadKanbanView } from "../file_upload_kanban/file_upload_kanban_view";
import { AccountMoveKanbanController } from "./account_move_kanban_controller";

export const accountMoveUploadKanbanView = {
    ...fileUploadKanbanView,
    Controller: AccountMoveKanbanController,
    buttonTemplate: "account.AccountMoveKanbanView.Buttons",
};

registry.category("views").add("account_documents_kanban", accountMoveUploadKanbanView);
