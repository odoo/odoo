/** @odoo-module **/

import { registry } from "@web/core/registry";

import { kanbanView } from "@web/views/kanban/kanban_view";
import { SalePdfHeaderFooterKanbanController } from "@sale_pdf_quote_builder/js/sale_pdf_header_footer_kanban/sale_pdf_header_footer_kanban_controller";
import { SalePdfHeaderFooterKanbanRenderer } from "@sale_pdf_quote_builder/js/sale_pdf_header_footer_kanban/sale_pdf_header_footer_kanban_renderer";

export const salePdfHeaderFooterKanbanView = {
    ...kanbanView,
    Controller: SalePdfHeaderFooterKanbanController,
    Renderer: SalePdfHeaderFooterKanbanRenderer,
    buttonTemplate: "sale_pdf_quote_builder.SalePdfHeaderFooterKanbanView.Buttons",
};

registry.category("views").add("sale_pdf_headers_footers_kanban", salePdfHeaderFooterKanbanView);
