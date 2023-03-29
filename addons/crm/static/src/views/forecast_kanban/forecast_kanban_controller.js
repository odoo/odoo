/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";

export class ForecastKanbanController extends KanbanController {
    isQuickCreateField(field) {
        return super.isQuickCreateField(...arguments) || (field && field.name === "date_deadline");
    }
}
