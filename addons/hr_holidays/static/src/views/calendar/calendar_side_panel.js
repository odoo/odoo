import { CalendarSidePanel } from "@web/views/calendar/calendar_side_panel/calendar_side_panel";
import { TimeOffCalendarFilterPanel } from "@hr_holidays/views/calendar/filter_panel/calendar_filter_panel";

export class TimeOffCalendarSidePanel extends CalendarSidePanel {
    static components = {
        ...TimeOffCalendarSidePanel.components,
        FilterPanel: TimeOffCalendarFilterPanel,
    };

    get filterPanelProps() {
        return {
            ...super.filterPanelProps,
            employee_id: this.props.model.employeeId,
        };
    }
}
