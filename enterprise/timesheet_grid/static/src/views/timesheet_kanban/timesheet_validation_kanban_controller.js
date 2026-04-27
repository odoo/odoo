/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";

export class TimesheetValidationKanbanController extends KanbanController {
    async validateTimesheet() {
        const result = await this.model.orm.call(this.props.resModel, "action_validate_timesheet", [
            this.props.resIds,
        ]);
        await this.model.notification.add(result.params.message, { type: result.params.type });
        this.render(true);
    }
}
