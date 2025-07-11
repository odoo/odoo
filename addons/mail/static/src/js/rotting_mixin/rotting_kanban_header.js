import { KanbanHeader } from "@web/views/kanban/kanban_header";
import { RottingColumnProgress } from "./rotting_column_progress";

export class RottingKanbanHeader extends KanbanHeader {
    static template = "mail.RottingKanbanHeader";
    static components = {
        ...KanbanHeader.components,
        ColumnProgress: RottingColumnProgress,
    };

    async onRotIconClicked() {
        await this.progressBarState.toggleFilterRotten(this.group.id);
    }
}
