import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";

export class ProductImageKanbanRenderer extends KanbanRenderer {
    getResequenceOrderIndex() {
        return 1;
    }
}
