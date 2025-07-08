import { useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CalendarMobileFilterPanel } from "@web/views/calendar/mobile_filter_panel/calendar_mobile_filter_panel";

export class TimeOffCalendarMobileFilterPanel extends CalendarMobileFilterPanel {
    static components = {
        ...CalendarMobileFilterPanel.components,
    };
    static template = "hr_holidays.TimeOffCalendarMobileFilterPanel";

    setup() {
        super.setup();

        this.orm = useService("orm");
        this.leaveState = useState({
            holidays: [],
        });
        onWillStart(this.loadFilterData);
        onWillUpdateProps(this.loadFilterData);
    }

    async loadFilterData() {
        if (!this.env.isSmall) {
            return;
        }
        const promises = [];
        for (const section of this.props.model.filterSections){

            if (section.fieldName !== "holiday_status_id") {
                continue;
            }
            promises.push(
                this.orm.call("hr.leave.type", "get_allocation_data_request", [])
            );
        }
        const filterData = {};
        const [data,] = await Promise.all(promises);
        if(!data){
            return;
        }
        data.forEach((leave) => {
            filterData[leave[3]] = leave;
        });
        this.leaveState.holidays = filterData;
    }

}
