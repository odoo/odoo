import { CalendarSidePanel } from "@web/views/calendar/calendar_side_panel/calendar_side_panel";
import { user } from "@web/core/user";

/**
 * Add the possibility to display/hide the activity events from the attendee calendar
 * by adding a filter in the calendar side panel.
 */
export class AttendeeCalendarSidePanel extends CalendarSidePanel {
    static components = {
        ...CalendarSidePanel.components,
    };
    static template = "calendar.AttendeeCalendarSidePanel";

    get activityFilterName() {
        return "Activities";
    }

    get showActivities() {
        return this.props.model.showActivities;
    }

    get showActivityFilter() {
        return Object.keys(this.props.model.data.activities).length;
    }

    async onActivityFilterInputChange(ev) {
        await user.setUserSettings("calendar_default_show_activities", ev.target.checked);
        await this.props.model.load();
    }
}
