/** @odoo-module **/

import { registry } from "@web/core/registry";
import { graphView } from "@web/views/graph/graph_view";
import { HelpdeskTicketGraphModel } from "./helpdesk_ticket_graph_model";

const helpdeskTicketGraphView = {
    ...graphView,
    Model: HelpdeskTicketGraphModel,
};

registry.category("views").add("helpdesk_ticket_graph", helpdeskTicketGraphView);
