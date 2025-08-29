import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { RottingKanbanRecord } from "./rotting_kanban_record";
import { RottingKanbanHeader } from "./rotting_kanban_header";

export class RottingKanbanRenderer extends KanbanRenderer {
    static components = {
        ...KanbanRenderer.components,
        KanbanRecord: RottingKanbanRecord,
        KanbanHeader: RottingKanbanHeader,
    };
    /**
     * @override
     */
    getGroupClasses(group, isGroupProcessing) {
        let classes = super.getGroupClasses(group, isGroupProcessing);
        if (this.props.progressBarState && this.props.progressBarState.rotIsFiltered[group.id]) {
            classes += " o_kanban_group_show o_kanban_group_show_rotting";
        }
        return classes;
    }
}
