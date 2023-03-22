/** @odoo-module **/

import { CalendarFilterPanel } from "@web/views/calendar/filter_panel/calendar_filter_panel";

export class ProjectCalendarFilterPanel extends CalendarFilterPanel { }

ProjectCalendarFilterPanel.subTemplates = {
    filter: "project.ProjectCalendarFilterPanel.filter",
};
