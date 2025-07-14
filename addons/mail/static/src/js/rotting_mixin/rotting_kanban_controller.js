import { KanbanController } from "@web/views/kanban/kanban_controller";

export class RottingKanbanController extends KanbanController {
    get progressBarAggregateFields() {
        const res = super.progressBarAggregateFields;
        if (this.props.fields.is_rotting) {
            res.push(this.props.fields.is_rotting);
        }
        return res;
    }
}
