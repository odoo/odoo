import { calendarView } from "@web/views/calendar/calendar_view";

import { TimeOffCalendarController } from "./calendar_controller";
import { TimeOffCalendarModel } from "./calendar_model";
import { TimeOffCalendarRenderer, TimeOffDashboardCalendarRenderer } from "./calendar_renderer";

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

export const timeOffCalendarHrLeaveView = {
    ...calendarView,
    Controller: TimeOffCalendarControllerHrLeave,
    Renderer: TimeOffCalendarRenderer,
    Model: TimeOffCalendarModel,
    buttonTemplate: "hr_holidays.CalendarController.Buttons",
};

registry.category("views").add("time_off_calendar_dashboard", {
    ...timeOffCalendarHrLeaveView,
    Renderer: TimeOffDashboardCalendarRenderer,
});

registry.category("views").add("time_off_management_calendar", {
    ...timeOffCalendarHrLeaveView,
    buttonTemplate: "hr_holidays.CalendarController.ManagementButtons",
});
