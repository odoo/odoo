import { KanbanRecord } from "@web/views/kanban/kanban_record";
import { isRecordRotting } from "./rotting_widget";

export class RottingKanbanRecord extends KanbanRecord {
    /**
     * @override
     */
    getRecordClasses() {
        let classes = super.getRecordClasses();
        if (isRecordRotting(this.props.record)) {
            classes += " oe_kanban_card_rotting";
        }
        return classes;
    }
}
