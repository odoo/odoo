import { CalendarSidePanel } from "@web/views/calendar/calendar_side_panel/calendar_side_panel";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";

/**
 * Add the possibility to display/hide the user pending activities from the attendee calendar
 * by adding a filter in the calendar side panel.
 */
export class AttendeeCalendarSidePanel extends CalendarSidePanel {
    static components = {
        ...CalendarSidePanel.components,
    };
    static template = "calendar.AttendeeCalendarSidePanel";

    setup() {
        super.setup();
        this.state.activityFilterChecked = this.showActivities;
    }

    get activityFilterName() {
        return _t("My Activities");
    }

    get showActivities() {
        return this.props.model.showActivities;
    }

    get showActivityFilter() {
        return this.props.model.userActivitiesEnabled && this.props.model.scale !== "year";
    }

    async onToggleActivityFilter() {
        this.state.activityFilterChecked = !this.state.activityFilterChecked;
        await user.setUserSettings("calendar_show_activities", this.state.activityFilterChecked);
        await this.props.model.load();
    }
}
