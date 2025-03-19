import { patch } from "@web/core/utils/patch";
import { useExceptionalDays } from "../../hooks";
import { TimeOffCalendarYearRenderer } from "@hr_holidays/views/calendar/year/calendar_year_renderer";

patch(TimeOffCalendarYearRenderer.prototype, {
    setup() {
        super.setup();
        this.exceptionalDays = useExceptionalDays(this.props);
    },

    async getMandatoryData(info, date) {
        if (info.dayEl.classList.contains("hr_exceptional_days")) {
            return await this.orm.call("hr.employee", "get_exceptional_days_data", [date, date]);
        } else {
            return super.getMandatoryData(info, date);
        }
    },

    getDayCellClassNames(info) {
        return [...super.getDayCellClassNames(info), ...this.exceptionalDays(info)];
    },
});
