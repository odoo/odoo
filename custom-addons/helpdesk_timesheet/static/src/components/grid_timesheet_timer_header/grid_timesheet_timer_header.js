/** @odoo-module **/

import { patch } from '@web/core/utils/patch';

import { GridTimesheetTimerHeader } from '@timesheet_grid/components/grid_timesheet_timer_header/grid_timesheet_timer_header';

patch(GridTimesheetTimerHeader.prototype, {
    /**
     * @override
     */
    get fieldNames() {
        return [...super.fieldNames, 'helpdesk_ticket_id'];
    },
});
