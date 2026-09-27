import { registry } from "@web/core/registry";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { IrAttachmentDownload } from "@mail/views/web/attachment/ir_attachment_download";

class IrAttachmentKanbanController extends IrAttachmentDownload(KanbanController) {}

export const irAttachmentKanbanView = {
    ...kanbanView,
    Controller: IrAttachmentKanbanController,
};

registry.category("views").add("ir_attachment_kanban", irAttachmentKanbanView);
