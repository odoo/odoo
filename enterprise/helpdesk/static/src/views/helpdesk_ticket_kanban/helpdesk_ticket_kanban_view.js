/** @odoo-module */

import { registry } from "@web/core/registry";
import { kanbanView } from '@web/views/kanban/kanban_view';
import { HelpdeskTicketRenderer } from './helpdesk_ticket_kanban_renderer';

export const helpdeskTicketKanbanView = {
    ...kanbanView,
    Renderer: HelpdeskTicketRenderer,
};

registry.category('views').add('helpdesk_ticket_kanban', helpdeskTicketKanbanView);
