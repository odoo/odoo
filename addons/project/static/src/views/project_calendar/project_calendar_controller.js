/** @odoo-module **/

import { CalendarController } from "@web/views/calendar/calendar_controller";
import { ProjectCalendarFilterPanel } from "./project_calendar_filter_panel/project_calendar_filter_panel";

export class ProjectCalendarController extends CalendarController {
    static components = {
        ...ProjectCalendarController.components,
        FilterPanel: ProjectCalendarFilterPanel,
    };
    setup() {
        super.setup(...arguments);
        this.env.config.setDisplayName(this.env.config.getDisplayName() + this.env._t(" - Tasks by Deadline"));
    }
}
