import { KanbanRecord } from "@web/views/kanban/kanban_record";

export class MrpWorkorderKanbanRecord extends KanbanRecord {
    getCardClasses(...args) {
        let classes = super.getCardClasses(args);
        if (this.record.production_state.raw_value == 'draft') {
            classes += " o_wo_draft";
        }
        if (this.record.state.raw_value == 'ready') {
            const start_datetime = luxon.DateTime.fromISO(this.record.date_start.raw_value);

            if (start_datetime.hasSame(luxon.DateTime.now(), 'day')) {
                classes += " o_wo_date_orange";
            }

            if (start_datetime.toISODate() < luxon.DateTime.now().toISODate()) {
                classes += " o_wo_date_red";
            }
        }
        if (this.record.remaining_time.raw_value < 0) {
            classes += " o_wo_remaining_red";
        }
        return classes;
    }
}
