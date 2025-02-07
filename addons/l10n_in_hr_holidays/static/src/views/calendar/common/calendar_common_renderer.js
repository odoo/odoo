import { patch } from "@web/core/utils/patch";
import { useExceptionalDays } from "../../hooks";
import { TimeOffCalendarCommonRenderer } from "@hr_holidays/views/calendar/common/calendar_common_renderer";

patch(TimeOffCalendarCommonRenderer.prototype, {
    setup() {
        super.setup();
        this.exceptionalDays = useExceptionalDays(this.props);
    },

    getDayCellClassNames(info) {
        return [...super.getDayCellClassNames(info), ...this.exceptionalDays(info)];
    },
});
