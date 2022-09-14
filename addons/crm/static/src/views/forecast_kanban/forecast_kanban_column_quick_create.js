/** @odoo-module **/

import { KanbanColumnQuickCreate } from "@web/views/kanban/kanban_column_quick_create";

export class ForecastKanbanColumnQuickCreate extends KanbanColumnQuickCreate {
    /**
     * @override
     *
     * Create column directly upon "unfolding" quick create.
     */
    unfold() {
        this.props.onValidate();
    }
}
