import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { MrpProductionKanbanHeader } from "./mrp_production_kanban_header";

export class MrpProductionKanbanRenderer extends KanbanRenderer {
    static components = {
        ...KanbanRenderer.components,
        KanbanHeader: MrpProductionKanbanHeader,
    };
}
