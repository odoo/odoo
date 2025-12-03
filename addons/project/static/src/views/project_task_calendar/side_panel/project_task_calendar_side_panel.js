import { CalendarSidePanel } from "@web/views/calendar/calendar_side_panel/calendar_side_panel";
import { ProjectTaskCalendarFilterSection } from "../project_task_calendar_filter_section/project_task_calendar_filter_section";

export class ProjectTaskCalendarSidePanel extends CalendarSidePanel {
    static components = {
        ...CalendarSidePanel.components,
        FilterSection: ProjectTaskCalendarFilterSection,
    };
}
