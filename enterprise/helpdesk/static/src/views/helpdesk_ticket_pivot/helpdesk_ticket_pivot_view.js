/** @odoo-module **/
import { registry } from "@web/core/registry";
import { pivotView } from "@web/views/pivot/pivot_view";
import { HelpdeskTicketPivotModel } from "./helpdesk_ticket_pivot_model";

const helpdeskTicketPivotView = {
    ...pivotView,
    Model: HelpdeskTicketPivotModel,
};

registry.category("views").add("helpdesk_ticket_pivot", helpdeskTicketPivotView);
