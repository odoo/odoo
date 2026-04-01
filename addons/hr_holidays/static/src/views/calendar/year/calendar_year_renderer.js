import { CalendarYearRenderer } from "@web/views/calendar/calendar_year/calendar_year_renderer";

import { useService } from "@web/core/utils/hooks";
import { useMandatoryDays } from "../../hooks";
import { useCalendarPopover } from "@web/views/calendar/hooks/calendar_popover_hook";
import { TimeOffCalendarYearPopover } from "./calendar_year_popover";

export class TimeOffCalendarYearRenderer extends CalendarYearRenderer {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.mandatoryDays = useMandatoryDays(this.props);
        this.mandatoryDaysList = [];
        this.mandatoryDayPopover = useCalendarPopover(TimeOffCalendarYearPopover);
    }

    get options() {
        return Object.assign(super.options, {
            weekNumbers: true,
        });
    }

    get customOptions() {
        return {
            ...super.customOptions,
            weekNumbersWithinDays: false,
        };
    }

    /** @override **/
    async onDateClick(info) {
        const is_mandatory_day = [...info.dayEl.classList].some((elClass) =>
            elClass.startsWith("hr_mandatory_day_")
        );
        this.mandatoryDayPopover.close();
        if (is_mandatory_day && !this.env.isSmall) {
            this.popover.close();
            const date = luxon.DateTime.fromISO(info.dateStr);
            const target = info.dayEl;
            const mandatory_days_data = await this.orm.call(
                "hr.employee",
                "get_mandatory_days_data",
                [date, date]
            );
            mandatory_days_data.forEach((mandatory_day_data) => {
                mandatory_day_data["start"] = luxon.DateTime.fromISO(mandatory_day_data["start"]);
                mandatory_day_data["end"] = luxon.DateTime.fromISO(mandatory_day_data["end"]);
            });
            const records = Object.values(this.props.model.records).filter((r) =>
                luxon.Interval.fromDateTimes(r.start.startOf("day"), r.end.endOf("day")).contains(
                    date
                )
            );
            const props = this.getPopoverProps(date, records);
            props["records"] = mandatory_days_data.concat(props["records"]);
            this.mandatoryDayPopover.open(target, props, "o_cw_popover_holidays o_cw_popover");
        } else {
            super.onDateClick(info);
        }
    }

    openPopover(target, date, records) {
        this.popover.open(target, this.getPopoverProps(date, records), "o_cw_popover_holidays o_cw_popover");
    }

    getDayCellClassNames(info) {
        return [...super.getDayCellClassNames(info), ...this.mandatoryDays(info)];
    }

    _halfDayStyleCache = new Set();
    ensureHalfDayClass(start, end) {
        const className = `o_event_half_${start}_${end}`;
        if (this._halfDayStyleCache.has(className)) return className;

        const css = `
            .fc-event-start.${className} {
                clip-path: polygon(${start}% 0%, 100% 0%, 100% 100%, ${start}% 100%);
            }
            .fc-event-end.${className} {
                clip-path: polygon(0% 0%, ${end}% 0%, ${end}% 100%, 0% 100%);
            }
            .fc-event-start.fc-event-end.${className} {
                clip-path: polygon(${start}% 0%, ${end}% 0%, ${end}% 100%, ${start}% 100%);
            }
        `;
        let styleSheet = document.getElementById('half-day-dynamic-styles');
        if (!styleSheet) {
            styleSheet = document.createElement('style');
            styleSheet.id = 'half-day-dynamic-styles';
            document.head.appendChild(styleSheet);
        }

        styleSheet.textContent += css;
        this._halfDayStyleCache.add(className);

        return className;
    }

    /**
     * @override
     */
    eventClassNames({ event }) {
    const classesToAdd = super.eventClassNames(...arguments);
    const record = this.props.model.records[event.id];
    if (record) {
        const isHalfStart = record.requestDateFromPeriod === "pm" ||
            (record?.rawRecord?.request_unit_hours && record.start.c.hour >= 12);
        const isHalfEnd = record.requestDateToPeriod === "am" ||
            (record?.rawRecord?.request_unit_hours && record.end.c.hour <= 12);

        if (!isHalfStart && !isHalfEnd) return classesToAdd;

        const isMultiWeek = record.start.localWeekNumber != record.end.localWeekNumber
        let start = 0;
        let end = 100;

        if (!isMultiWeek) {
            const lastRowStart = record.start > record.end.startOf('month') ? record.start : record.end.startOf('month');
            const firstRowEnd = record.end < record.start.endOf('month') ? record.end : record.start.endOf('month');
            const daysInFirstRow = firstRowEnd.startOf('day').diff(record.start.startOf('day'), 'days').days + 1;
            const daysInLastRow = record.end.startOf('day').diff(lastRowStart.startOf('day'), 'days').days + 1;

            start = isHalfStart ? Math.round(50 / daysInFirstRow) : 0;
            end = isHalfEnd ? Math.round(100 - (50 / daysInLastRow)) : 100;
        }
        else {
            // Multi-week: first slice — only care about start
            if (isHalfStart) {
                const rowEnd = record.start.endOf('week') < record.start.endOf('month')
                    ? record.start.endOf('week').minus({ days: 1 })
                    : record.start.endOf('month');
                const daysInFirstRow = rowEnd.startOf('day').diff(record.start.startOf('day'), 'days').days + 1;
                start = Math.round(50 / daysInFirstRow);
            }
            // Multi-week: last slice — only care about end
            if (isHalfEnd) {
                const rowStart = record.end.startOf('week') > record.end.startOf('month')
                    ? record.end.startOf('week').minus({ days: 1 })
                    : record.end.startOf('month');
                const daysInLastRow = record.end.startOf('day').diff(rowStart.startOf('day'), 'days').days + 1;
                end = Math.round(100 - (50 / daysInLastRow));
            }
        }

        classesToAdd.push(this.ensureHalfDayClass(start, end));
    }
    return classesToAdd;
}
}
