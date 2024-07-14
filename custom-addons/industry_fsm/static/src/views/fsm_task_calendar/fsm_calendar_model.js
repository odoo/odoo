/** @odoo-module */

import { ProjectTaskCalendarModel } from '@project/views/project_task_calendar/project_task_calendar_model';

export class FsmTaskCalendarModel extends ProjectTaskCalendarModel {
    makeContextDefaults(record) {
        const { default_planned_date_start, ...context } = super.makeContextDefaults(record);
        return {
            ...context,
            default_planned_date_begin: default_planned_date_start,
        };
    }
}
