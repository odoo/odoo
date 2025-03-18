import { CalendarFilterPanel } from "@web/views/calendar/filter_panel/calendar_filter_panel";
import { TimeOffCardMobile } from "../../../dashboard/time_off_card";

import { useService } from "@web/core/utils/hooks";
import { useState, onWillStart } from "@odoo/owl";

export class TimeOffCalendarFilterPanel extends CalendarFilterPanel {
    static components = {
        ...CalendarFilterPanel.components,
        TimeOffCardMobile,
    };
    static subTemplates = {
        filter: "hr_holidays.CalendarFilterPanel.filter",
    };

    setup() {
        super.setup();

        this.orm = useService("orm");
        this.leaveState = useState({
            holidays: [],
        });

        onWillStart(this.loadFilterData);
    }

    async loadFilterData() {
        if (!this.env.isSmall) {
            return;
        }

        const filterData = {};
        const data = await this.orm.call("hr.leave.type", "get_allocation_data_request", []);

        data.forEach((leave) => {
            filterData[leave[3]] = leave;
        });
        this.leaveState.holidays = filterData;
    }
}
