/** @odoo-module **/

import { TaskGanttController } from '@project_enterprise/task_gantt_controller';
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

patch(TaskGanttController.prototype, {
    /**
     * @override
    */
    onAddClicked() {
        const { context } = this.model.searchParams;
        const { startDate, stopDate } = this.model.metaData;
        const today = DateTime.local().startOf("day");
        // similar to what is found in planning_gantt_controller.js but different
        // --> unify?
        if (context.fsm_mode && startDate <= today.endOf("day") && today <= stopDate) {
            const stop = today.endOf("day");
            const context = this.model.getDialogContext({ start: today, stop, withDefault: true });
            this.create(context);
            return;
        }
        super.onAddClicked(...arguments);
    },
});
