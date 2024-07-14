/** @odoo-module */

import { registry } from "@web/core/registry";
import { listView } from '@web/views/list/list_view';
import { HelpdeskTicketListRenderer } from "./helpdesk_ticket_list_renderer";

export const helpdeskTicketListView = {
    ...listView,
    Renderer: HelpdeskTicketListRenderer,
};

registry.category("views").add("helpdesk_ticket_list", helpdeskTicketListView);
