import { KanbanRecord } from "@web/views/kanban/kanban_record";

export class RottingKanbanRecord extends KanbanRecord {
    /**
     * @override
     */
    getRecordClasses() {
        let ret = super.getRecordClasses();
        if (this.props.record.data.is_rotting) {
            ret += " o_mail_resource_card_rotting_bg";
        }
        return ret;
    }
}
