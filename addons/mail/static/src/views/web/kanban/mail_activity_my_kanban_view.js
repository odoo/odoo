import { kanbanView } from "@web/views/kanban/kanban_view";
import { MailActivityMyKanbanController } from "./mail_activity_my_kanban_controller";
import { registry } from "@web/core/registry";

export const mailActivityMyKanbanView = {
    ...kanbanView,
    Controller: MailActivityMyKanbanController,
};

registry.category("views").add("mail_activity_my_kanban", mailActivityMyKanbanView);
