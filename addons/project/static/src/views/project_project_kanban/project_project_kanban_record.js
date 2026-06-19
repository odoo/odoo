import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { RottingKanbanRecord } from "@mail/js/rotting_mixin/rotting_kanban_record";

export class ProjectProjectKanbanRecord extends KanbanRecord {
    /**
     * @override
     */
    get isMenuVisible() {
        return super.isMenuVisible || true;
    }
}

export class ProjectProjectKanbanGroupStageRecord extends RottingKanbanRecord {
    /**
     * @override
     */
    get isMenuVisible() {
        return super.isMenuVisible || true;
    }
}
