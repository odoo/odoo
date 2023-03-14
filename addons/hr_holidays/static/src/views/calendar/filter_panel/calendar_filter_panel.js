/** @odoo-module */

import { CalendarFilterPanel } from "@web/views/calendar/filter_panel/calendar_filter_panel";
import { TimeOffCardMobile } from "../../../dashboard/time_off_card";
import { getFormattedDateSpan } from '@web/views/calendar/utils';

import { useService } from "@web/core/utils/hooks";
import { serializeDate } from "@web/core/l10n/dates";

const { useState, onWillStart, onWillUpdateProps } = owl;

export class TimeOffCalendarFilterPanel extends CalendarFilterPanel {
    setup() {
        super.setup();

        this.orm = useService('orm');
        this.getFormattedDateSpan = getFormattedDateSpan;
        this.leaveState = useState({
            holidays: [],
            stressDays: [],
            bankHolidays: [],
        });

        onWillStart(async () => {
            await this.loadFilterData();
            await this.updateSpecialDays();
        });
        onWillUpdateProps(this.updateSpecialDays);
    }

    async updateSpecialDays() {
        const context = {
            'employee_id': this.props.employee_id,
        }
        const specialDays = await this.orm.call(
            'hr.employee', 'get_special_days_data', [
                serializeDate(this.props.model.rangeStart, "datetime"),
                serializeDate(this.props.model.rangeEnd, "datetime"),
            ],
            {
                'context': context,
            },
        );
        specialDays['bankHolidays'].forEach(bankHoliday => {
            bankHoliday.start = luxon.DateTime.fromISO(bankHoliday.start)
            bankHoliday.end = luxon.DateTime.fromISO(bankHoliday.end)
        });
        specialDays['stressDays'].forEach(stressDay => {
            stressDay.start = luxon.DateTime.fromISO(stressDay.start)
            stressDay.end = luxon.DateTime.fromISO(stressDay.end)
        });
        this.leaveState.bankHolidays = specialDays['bankHolidays'];
        this.leaveState.stressDays = specialDays['stressDays'];
    }

    async loadFilterData() {
        if(!this.env.isSmall) {
            return;
        }

        const filterData = {};
        const data = await this.orm.call(
            'hr.leave.type', 'get_days_all_request', [],
        );

        data.forEach((leave) => {
            filterData[leave[3]] = leave;
        });
        this.leaveState.holidays = filterData;
    }
}
TimeOffCalendarFilterPanel.template = 'hr_holidays.CalendarFilterPanel';
TimeOffCalendarFilterPanel.components = {
    ...TimeOffCalendarFilterPanel.components,
    TimeOffCardMobile,
}
TimeOffCalendarFilterPanel.subTemplates = {
    filter: "hr_holidays.CalendarFilterPanel.filter",
}
