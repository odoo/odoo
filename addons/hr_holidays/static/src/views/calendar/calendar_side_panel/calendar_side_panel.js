import { CalendarSidePanel } from "@web/views/calendar/calendar_side_panel/calendar_side_panel";
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { Cache } from "@web/core/utils/cache";
import { useService } from "@web/core/utils/hooks";
import { useState, onWillStart, onWillUpdateProps } from "@odoo/owl";

export class TimeOffCalendarSidePanel extends CalendarSidePanel {
    static components = {
        ...CalendarSidePanel.components,
    };
    static template = "hr_holidays.TimeOffCalendarSidePanel";

    setup() {
        super.setup();

        this.orm = useService("orm");
        this.getFormattedDateSpan = function getFormattedDateSpan(start, end) {
            const n = "numeric";
            const s = "short";
            const isSameDay = start.hasSame(end, "days");
            if (isSameDay) {
                return start.toLocaleString({ month: s, day: n, year: n });
            }
            return start.toLocaleString({ month: s, day: n, year: n }) + " - " + end.toLocaleString({ month: s, day: n, year: n });
        };;
        this.leaveState = useState({
            mandatoryDays: [],
            bankHolidays: [],
            holidays: [],
        });

        this._specialDaysCache = new Cache(
            (start, end) => this.fetchSpecialDays(start, end),
            (start, end) => `${serializeDateTime(start)},${serializeDateTime(end)}`
        );

        onWillStart(async () => {
            await this.updateSpecialDays();
            await this.loadHolidayData();
        });
        onWillUpdateProps(async () => {
            await this.updateSpecialDays();
            await this.loadHolidayData();
        });
        
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

    async loadHolidayData() {
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
        this.leaveState.holidays = Object.values(filterData);
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
