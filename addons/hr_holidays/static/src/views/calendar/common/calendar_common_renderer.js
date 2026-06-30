import { onWillStart } from "@odoo/owl";
import { user } from "@web/core/user";
import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { useMandatoryDays } from "../../hooks";

export class TimeOffCalendarCommonRenderer extends CalendarCommonRenderer {
    setup() {
        super.setup();
        this.mandatoryDays = useMandatoryDays(this.props);
        onWillStart(async () => {
            this.isManager = await user.hasGroup("hr_holidays.group_hr_holidays_user");
        });
    }

    getDayCellClassNames(info) {
        return [...super.getDayCellClassNames(info), ...this.mandatoryDays(info)];
    }

    onClick(info) {
        // To open record view
        return this.onDblClick(info);
    }
}
