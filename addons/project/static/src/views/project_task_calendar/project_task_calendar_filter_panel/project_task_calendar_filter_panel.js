/** @odoo-module **/

import { CalendarFilterPanel } from "@web/views/calendar/filter_panel/calendar_filter_panel";

export class ProjectTaskCalendarFilterPanel extends CalendarFilterPanel { 
    static subTemplates = {
        filter: "project.ProjectTaskCalendarFilterPanel.filter",
    };
}
