/** @odoo-module **/

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { IrCronDashboard } from "@cron_visualization/ir_cron_kanban_view/ir_cron_dashboard";

export class IrCronKanbanRenderer extends KanbanRenderer {

}

IrCronKanbanRenderer.template = "cron_visualization.IrCronKanbanRenderer";
IrCronKanbanRenderer.components = Object.assign({}, KanbanRenderer.components, {IrCronDashboard})
