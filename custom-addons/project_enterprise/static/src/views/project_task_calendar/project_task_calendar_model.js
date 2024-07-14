/** @odoo-module */

import { deserializeDate } from "@web/core/l10n/dates";
import { ProjectTaskCalendarModel } from '@project/views/project_task_calendar/project_task_calendar_model';

export class ProjectEnterpriseTaskCalendarModel extends ProjectTaskCalendarModel {
    makeContextDefaults(record) {
        const { default_planned_date_start, ...context } = super.makeContextDefaults(record);
        if (!deserializeDate(default_planned_date_start).hasSame(deserializeDate(context["default_date_deadline"]), 'day')) {
            context.default_planned_date_begin = default_planned_date_start;
        }
        return context;
    }
}
