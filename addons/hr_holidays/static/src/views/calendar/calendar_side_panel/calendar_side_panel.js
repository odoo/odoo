import { CalendarSidePanel } from "@web/views/calendar/calendar_side_panel/calendar_side_panel";
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { Cache } from "@web/core/utils/cache";
import { useService } from "@web/core/utils/hooks";
import { asyncComputed, onWillStart } from "@odoo/owl";

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
            return (
                start.toLocaleString({ month: s, day: n, year: n }) +
                " - " +
                end.toLocaleString({ month: s, day: n, year: n })
            );
        };

        this._specialDaysCache = new Cache(
            (start, end) => this.fetchSpecialDays(start, end),
            (start, end) => `${serializeDateTime(start)},${serializeDateTime(end)}`
        );

        this.currentDateTime = luxon.DateTime.now();

        this.specialDays = asyncComputed(() => this.getSpecialDays());
        this.holidays = asyncComputed(() => this.getHolidayData());

        onWillStart(async () => {
            await Promise.all([
                this.specialDays.currentPromise(),
                this.holidays.currentPromise(),
            ]);
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

    async getHolidayData() {
        if (!this.env.isSmall) {
            return;
        }
        const promises = [];
        for (const section of this.props.model.filterSections) {
            if (section.fieldName !== "work_entry_type_id") {
                continue;
            }
            promises.push(
                this.orm.call("hr.work.entry.type", "get_allocation_data_request", [], {
                    context: { from_dashboard: true },
                })
            );
        }
        const filterData = {};
        const [data] = await Promise.all(promises);
        if (!data) {
            return;
        }
        data.forEach((leave) => {
            filterData[leave[3]] = leave;
        });
        return Object.values(filterData);
    }

    async getSpecialDays() {
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
        return {
            bankHolidays: specialDays.bankHolidays,
            mandatoryDays: specialDays.mandatoryDays,
        };
    }

    get leaveState() {
        return {
            bankHolidays: this.specialDays()?.bankHolidays || [],
            mandatoryDays: this.specialDays()?.mandatoryDays || [],
            holidays: this.holidays() || [],
        };
    }
}
