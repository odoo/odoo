import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { MailingTemplateKanbanIframe } from "./mailing_template_kanban_iframe";

export const mailingTemplateKanbanView = {
    ...kanbanView,
    Renderer: MailingTemplateKanbanIframe,
};

registry.category("views").add("mailing_template_kanban_view", mailingTemplateKanbanView);
