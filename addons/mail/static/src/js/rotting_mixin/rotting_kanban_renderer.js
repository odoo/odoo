import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { RottingKanbanRecord } from "./rotting_kanban_record";
import { RottingKanbanHeader } from "./rotting_kanban_header";

export class RottingKanbanRenderer extends KanbanRenderer {
    static components = {
        ...KanbanRenderer.components,
        KanbanRecord: RottingKanbanRecord,
        KanbanHeader: RottingKanbanHeader,
    };
}
