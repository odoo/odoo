/** @odoo-module **/

import { CalendarFilterPanel } from "@web/views/calendar/filter_panel/calendar_filter_panel";

export class PlanningCalendarFilterPanel extends CalendarFilterPanel {
    static subTemplates = {
        filter: "planning.PlanningCalendarFilterPanel.filter",
    };

    getNoColor(filter) {
        return this.section.fieldName == 'resource_id' ? 'no_filter_color' : '';
    }
}
