/** @odoo-module */

import { CalendarRenderer } from '@web/views/calendar/calendar_renderer';

import { TimeOffCalendarCommonRenderer } from './common/calendar_common_renderer';
import { TimeOffCalendarYearRenderer } from './year/calendar_year_renderer';

import { TimeOffDashboard } from '../../dashboard/time_off_dashboard';

export class TimeOffCalendarRenderer extends CalendarRenderer {
    get employeeId() {
        return this.props.model.employeeId;
    }

    get showDashboard() {
        return false;
    }
}
TimeOffCalendarRenderer.template = 'hr_holidays.CalendarRenderer';
TimeOffCalendarRenderer.components = {
    ...TimeOffCalendarRenderer.components,
    day: TimeOffCalendarCommonRenderer,
    week: TimeOffCalendarCommonRenderer,
    month: TimeOffCalendarCommonRenderer,
    year: TimeOffCalendarYearRenderer,
    TimeOffDashboard,
};

export class TimeOffDashboardCalendarRenderer extends TimeOffCalendarRenderer {
    get showDashboard() {
        return !this.env.isSmall;
    }
}
