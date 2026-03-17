import { calendarView } from '@web/views/calendar/calendar_view';

import { TimeOffCalendarController, TimeOffReportCalendarController } from './calendar_controller';
import { TimeOffCalendarModel } from './calendar_model';
import { TimeOffCalendarRenderer, TimeOffDashboardCalendarRenderer } from './calendar_renderer';

import { registry } from '@web/core/registry';
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { onWillStart } from "@odoo/owl";

class TimeOffCalendarControllerHrTime extends TimeOffCalendarController {
    setup() {
        super.setup();
        this.actionService = useService("action");
        onWillStart(async () => {
            this.canCreateGroupTimeOff = await user.hasGroup("hr_time.group_hr_time_responsible");
        });
    }

    async onNewGroupTimeOff() {
        await this.actionService.doAction("hr_time.action_hr_time_generate_multi_wizard");
    }
}

const TimeOffCalendarView = {
    ...calendarView,

    Controller: TimeOffCalendarController,
    Renderer: TimeOffCalendarRenderer,
    Model: TimeOffCalendarModel,
}

const TimeOffCalendarHrTimeView = {
    ...TimeOffCalendarView,
    Controller: TimeOffCalendarControllerHrTime,
    buttonTemplate: "hr_time.CalendarView.Buttons",
}

registry.category('views').add('time_off_calendar', TimeOffCalendarView);
registry.category('views').add('time_off_calendar_hr_time', TimeOffCalendarHrTimeView);
registry.category('views').add('time_off_calendar_dashboard', {
    ...TimeOffCalendarView,
    Renderer: TimeOffDashboardCalendarRenderer,
});
registry.category('views').add('time_off_report_calendar', {
    ...TimeOffCalendarView,
    Controller: TimeOffReportCalendarController,
})
