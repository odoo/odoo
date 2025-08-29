import { KanbanHeader } from "@web/views/kanban/kanban_header";
import { RottingColumnProgress } from "./rotting_column_progress";

export class RottingKanbanHeader extends KanbanHeader {
    static template = "mail.RottingKanbanHeader";
    static components = {
        ...KanbanHeader.components,
        ColumnProgress: RottingColumnProgress,
    };

    onRotIconClicked(group) {
        this.props.progressBarState.toggleFilterRotten(group);
    }
}
