/** @odoo-module **/

import { registry } from "@web/core/registry";
import { projectTaskCalendarView } from "@project/views/project_task_calendar/project_task_calendar_view";
import { ProjectEnterpriseTaskCalendarModel } from "./project_task_calendar_model";
import { ProjectTaskCalendarRenderer } from "./project_task_calendar_renderer";
import { ProjectTaskSearchModel } from "../project_task_search_model";

export const projectEnterpriseTaskCalendarView = {
    ...projectTaskCalendarView,
    Model: ProjectEnterpriseTaskCalendarModel,
    Renderer: ProjectTaskCalendarRenderer,
    SearchModel: ProjectTaskSearchModel,
};

registry.category("views").add("project_enterprise_task_calendar", projectEnterpriseTaskCalendarView);
