import { patch } from "@web/core/utils/patch";
import { serializeDate } from "@web/core/l10n/dates";
import { TimeOffCalendarFilterPanel } from "@hr_holidays/views/calendar/filter_panel/calendar_filter_panel";

patch(TimeOffCalendarFilterPanel.prototype, {
    setup() {
        super.setup();
        this.leaveState = {
            ...this.leaveState,
            exceptionalHoliday: [],
        };
    },
    async updateSpecialDays() {
        await super.updateSpecialDays();
        const exceptionDays = await this.orm.call(
            "hr.employee",
            "get_exceptional_days_data",
            [
                serializeDate(this.props.model.rangeStart, "datetime"),
                serializeDate(this.props.model.rangeEnd, "datetime"),
            ],
            {
                context: { employee_id: this.props.employee_id },
            }
        );
        exceptionDays.forEach((mandatoryDay) => {
            mandatoryDay.start = luxon.DateTime.fromISO(mandatoryDay.start);
            mandatoryDay.end = luxon.DateTime.fromISO(mandatoryDay.end);
        });
        this.leaveState.exceptionalHoliday = exceptionDays;
    },
});
