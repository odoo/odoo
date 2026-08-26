import { KanbanController } from "@web/views/kanban/kanban_controller";
import { RottingProgressBarState } from "./rotting_progress_bar_hook";

export class RottingKanbanController extends KanbanController {
    static ProgressBarStateClass = RottingProgressBarState;

    get progressBarAggregateFields() {
        const res = super.progressBarAggregateFields;
        if (this.props.fields.is_rotting) {
            res.push(this.props.fields.is_rotting);
        }
        return res;
    }
}
