import { KanbanController } from "@web/views/kanban/kanban_controller";

export class RottingKanbanController extends KanbanController {
    get progressBarAggregateFields() {
        const res = super.progressBarAggregateFields;
        const progressAttributes = this.props.archInfo.progressAttributes;
        if (progressAttributes && progressAttributes.rotting_count_field) {
            res.push(progressAttributes.rotting_count_field);
        }
        return res;
    }
}
