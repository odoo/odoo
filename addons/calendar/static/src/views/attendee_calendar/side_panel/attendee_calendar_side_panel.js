import { AttendeeCalendarCalendarFilterSection } from "../filter_section/attendee_calendar_calendar_filter_section";
import { AttendeeCalendarFilterSection } from "../filter_section/attendee_calendar_filter_section";
import { CalendarSidePanel } from "@web/views/calendar/calendar_side_panel/calendar_side_panel";

export class AttendeeCalendarSidePanel extends CalendarSidePanel {
    static components = {
        ...CalendarSidePanel.components,
        AttendeeCalendarCalendarFilterSection,
        FilterSection: AttendeeCalendarFilterSection,
    };
    static template = "calendar.AttendeeCalendarSidePanel";

    /**
     * @override
     */
    get sortedFilterSections() {
        return this.props.model.filterSections.sort((a, b) => b.fieldName.localeCompare(a.fieldName));
    }
}
