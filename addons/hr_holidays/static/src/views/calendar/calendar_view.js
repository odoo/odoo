import { calendarView } from "@web/views/calendar/calendar_view";

import { TimeOffCalendarController, TimeOffReportCalendarController } from "./calendar_controller";
import { TimeOffCalendarModel } from "./calendar_model";
import { TimeOffCalendarRenderer, TimeOffDashboardCalendarRenderer } from "./calendar_renderer";
import { TimeOffReportCalendarSearchModel } from "./time_off_search_model";

import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { onWillStart } from "@odoo/owl";

class TimeOffCalendarControllerHrLeave extends TimeOffCalendarController {
    setup() {
        super.setup();
        this.actionService = useService("action");
        onWillStart(async () => {
            this.canCreateGroupTimeOff = await user.hasGroup(
                "hr_holidays.group_hr_holidays_responsible"
            );
        });
    }

    async onNewGroupTimeOff() {
        await this.actionService.doAction("hr_holidays.action_hr_leave_generate_multi_wizard");
    }
}

const TimeOffCalendarHrLeaveView = {
    ...calendarView,
    Controller: TimeOffCalendarControllerHrLeave,
    Renderer: TimeOffCalendarRenderer,
    Model: TimeOffCalendarModel,
    buttonTemplate: "hr_holidays.CalendarView.Buttons",
};
registry.category("views").add("time_off_calendar_hr_leave", TimeOffCalendarHrLeaveView);

registry.category("views").add("time_off_calendar_dashboard", {
    ...TimeOffCalendarHrLeaveView,
    Renderer: TimeOffDashboardCalendarRenderer,
});

registry.category("views").add("time_off_report_calendar", {
    ...TimeOffCalendarHrLeaveView,
    Controller: TimeOffReportCalendarController,
    SearchModel: TimeOffReportCalendarSearchModel,
});
