/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from '@web/core/utils/patch';
import { GridTimesheetTimerHeader } from '@timesheet_grid/components/grid_timesheet_timer_header/grid_timesheet_timer_header';

patch(GridTimesheetTimerHeader.prototype, {
    /**
     * @override
     */
    get fieldNames() {
        return [...super.fieldNames, 'helpdesk_ticket_id'];
    },

    getFieldInfo(fieldName) {
        const fieldInfo = super.getFieldInfo(fieldName);
        if (fieldName === "helpdesk_ticket_id") {
            fieldInfo.context = `{ 'default_project_id': project_id, 'search_default_my_ticket': True, 'search_default_is_open': True, 'search_view_ref': 'helpdesk.helpdesk_ticket_view_search_analysis'}`;
            fieldInfo.placeholder = _t("Ticket");
        }
        return fieldInfo;
    },
});
