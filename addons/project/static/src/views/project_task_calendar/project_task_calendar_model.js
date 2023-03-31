/** @odoo-module */

import { CalendarModel } from '@web/views/calendar/calendar_model';

export class ProjectTaskCalendarModel extends CalendarModel {
    /**
     * @override
     */
    get defaultFilterLabel() {
        this.isCheckProject = 'project_id' in this.meta.filtersInfo;
        if (this.isCheckProject) {
            return this.env._t("Private");
        }
        return super.onWillStart();
    }
}
