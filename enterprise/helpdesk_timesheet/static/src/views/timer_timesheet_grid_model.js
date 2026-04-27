/** @odoo-module */

import { TimerGridRow } from "@timesheet_grid/views/timer_timesheet_grid/timer_timesheet_grid_model";
import { patch } from "@web/core/utils/patch";


patch(TimerGridRow.prototype, {
    /**
     * @override
     */
    get timeData() {
        return Object.assign(
            super.timeData, { helpdesk_ticket_id: this.valuePerFieldName?.helpdesk_ticket_id?.[0],},
        );
    }
});
