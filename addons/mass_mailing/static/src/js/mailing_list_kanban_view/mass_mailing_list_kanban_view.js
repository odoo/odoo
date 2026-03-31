import { kanbanView } from "@web/views/kanban/kanban_view";
import { MailingListKanbanController } from "./mass_mailing_list_kanban_controller";
import { registry } from "@web/core/registry";

export const MailingListKanbanView = {
    ...kanbanView,
    Controller: MailingListKanbanController,
};
registry.category("views").add("mailing_list_kanban_view", MailingListKanbanView);
