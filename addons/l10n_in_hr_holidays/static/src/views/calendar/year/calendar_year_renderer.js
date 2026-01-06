import { patch } from "@web/core/utils/patch";
import { useOptionalHolidays } from "../../hooks";
import { TimeOffCalendarYearRenderer } from "@hr_holidays/views/calendar/year/calendar_year_renderer";

patch(TimeOffCalendarYearRenderer.prototype, {

    setup() {
        super.setup();
        this.optionalHolidays = useOptionalHolidays(this.props);
    },

    getDayCellClassNames(info) {
        return [...super.getDayCellClassNames(info), ...this.optionalHolidays(info)];
    }
});
