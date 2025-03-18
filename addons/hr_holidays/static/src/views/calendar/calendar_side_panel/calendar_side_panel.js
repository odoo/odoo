import { getFormattedDateSpan } from "@web/views/calendar/utils";

import { CalendarSidePanel } from "@web/views/calendar/calendar_side_panel/calendar_side_panel";
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { Cache } from "@web/core/utils/cache";
import { useService } from "@web/core/utils/hooks";
import { useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { TimeOffCalendarFilterPanel } from "../filter_panel/calendar_filter_panel";

export class TimeOffCalendarSidePanel extends CalendarSidePanel {
    static components = {
        ...CalendarSidePanel.components,
        FilterPanel: TimeOffCalendarFilterPanel,
    };
    static template = "hr_holidays.TimeOffCalendarSidePanel";

    setup() {
        super.setup();

        this.orm = useService("orm");
        this.getFormattedDateSpan = getFormattedDateSpan;
        this.leaveState = useState({
            mandatoryDays: [],
            bankHolidays: [],
        });

        this._specialDaysCache = new Cache(
            (start, end) => this.fetchSpecialDays(start, end),
            (start, end) => `${serializeDateTime(start)},${serializeDateTime(end)}`
        );

        onWillStart(this.updateSpecialDays);
        onWillUpdateProps(this.updateSpecialDays);
    }

    fetchSpecialDays(start, end) {
        const context = {
            employee_id: this.props.model.employeeId,
        };
        return this.orm.call(
            "hr.employee",
            "get_special_days_data",
            [serializeDate(start, "datetime"), serializeDate(end, "datetime")],
            {
                context: context,
            }
        );
    }

    async updateSpecialDays() {
        const { rangeStart, rangeEnd } = this.props.model;
        const specialDays = await this._specialDaysCache.read(rangeStart, rangeEnd);
        specialDays["bankHolidays"].forEach((bankHoliday) => {
            bankHoliday.start = luxon.DateTime.fromISO(bankHoliday.start);
            bankHoliday.end = luxon.DateTime.fromISO(bankHoliday.end);
        });
        specialDays["mandatoryDays"].forEach((mandatoryDay) => {
            mandatoryDay.start = luxon.DateTime.fromISO(mandatoryDay.start);
            mandatoryDay.end = luxon.DateTime.fromISO(mandatoryDay.end);
        });
        this.leaveState.bankHolidays = specialDays["bankHolidays"];
        this.leaveState.mandatoryDays = specialDays["mandatoryDays"];
    }
}
