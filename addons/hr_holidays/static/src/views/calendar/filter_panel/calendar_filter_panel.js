/** @odoo-module */

import { CalendarFilterPanel } from "@web/views/calendar/filter_panel/calendar_filter_panel";
import { TimeOffCardMobile } from "../../../dashboard/time_off_card";

import { useService } from "@web/core/utils/hooks";

const { useState, onWillStart } = owl;

export class TimeOffCalendarFilterPanel extends CalendarFilterPanel {
    setup() {
        super.setup();

        this.orm = useService('orm');
        this.leaveState = useState({
            holidays: [],
        });

        onWillStart(async () => {
            await this.loadFilterData();
        });
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
