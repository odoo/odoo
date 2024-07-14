/** @odoo-module **/

import { registry } from "@web/core/registry";
import { projectTaskCalendarView } from "@project/views/project_task_calendar/project_task_calendar_view";
import { ProjectEnterpriseTaskCalendarModel } from "./project_task_calendar_model";

export const projectEnterpriseTaskCalendarView = {
    ...projectTaskCalendarView,
    Model: ProjectEnterpriseTaskCalendarModel,
};

registry.category("views").add("project_enterprise_task_calendar", projectEnterpriseTaskCalendarView);
