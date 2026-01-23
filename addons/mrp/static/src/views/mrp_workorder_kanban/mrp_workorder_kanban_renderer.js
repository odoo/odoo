/** @odoo-module **/

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { MrpWorkorderKanbanHeader } from "./mrp_workorder_kanban_header";

export class MrpWorkorderKanbanRenderer extends KanbanRenderer {
    static components = {
        ...KanbanRenderer.components,
        KanbanHeader: MrpWorkorderKanbanHeader,
    };
}
