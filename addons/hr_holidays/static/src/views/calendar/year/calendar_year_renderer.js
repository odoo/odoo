import { CalendarYearRenderer } from "@web/views/calendar/calendar_year/calendar_year_renderer";
import { useService } from "@web/core/utils/hooks";
import { useMandatoryDays } from "../../hooks";
import { useCalendarPopover } from "@web/views/calendar/hooks/calendar_popover_hook";
import { TimeOffCalendarYearPopover } from "./calendar_year_popover";
import { getLeaveLastMoment } from "../utils";

export class TimeOffCalendarYearRenderer extends CalendarYearRenderer {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.mandatoryDays = useMandatoryDays(this.props);
        this.mandatoryDaysList = [];
        this.mandatoryDayPopover = useCalendarPopover(TimeOffCalendarYearPopover);
        this.popover = useCalendarPopover(TimeOffCalendarYearPopover);
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

    /** The leaves a day holds, each counted from its first day to its last. */
    getLeavesForDate(date) {
        return Object.values(this.props.model.records).filter((leave) =>
            luxon.Interval.fromDateTimes(
                leave.start.startOf("day"),
                getLeaveLastMoment(leave).endOf("day")
            ).contains(date)
        );
    }

    /**
     * @override
     * A mandatory day opens its own popover, listing the day itself above the time off.
     */
    async onDateClick(info) {
        const is_mandatory_day = [...info.dayEl.classList].some((elClass) =>
            elClass.startsWith("hr_mandatory_day_")
        );
        this.mandatoryDayPopover.close();
        if (this.uiService.isSmall) {
            return super.onDateClick(info);
        }
        this.popover.close();

        // With date value we don't want to change the time, we need the exact date
        const date = luxon.DateTime.fromISO(info.dateStr);
        const target = info.dayEl;
        const leaves = this.getLeavesForDate(date);

        if (is_mandatory_day) {
            const mandatory_days_data = await this.orm.call(
                "hr.employee",
                "get_mandatory_days_data",
                [date, date]
            );
            mandatory_days_data.forEach((mandatory_day_data) => {
                mandatory_day_data["start"] = luxon.DateTime.fromISO(mandatory_day_data["start"]);
                mandatory_day_data["end"] = luxon.DateTime.fromISO(mandatory_day_data["end"]);
            });
            const props = this.getPopoverProps(date, leaves);
            props["records"] = mandatory_days_data.concat(props["records"]);
            this.mandatoryDayPopover.open(target, props, "o_cw_popover_holidays o_cw_popover");
        } else if (leaves.length) {
            this.openPopover(target, date, leaves);
        } else if (this.props.model.canCreate) {
            this.props.createRecord({ start: date, isAllDay: true });
        }
    }

    openPopover(target, date, records) {
        this.popover.open(
            target,
            this.getPopoverProps(date, records),
            "o_cw_popover_holidays o_cw_popover"
        );
    }

    getDayCellClassNames(info) {
        return [...super.getDayCellClassNames(info), ...this.mandatoryDays(info)];
    }

    _halfDayStyleCache = new Set();
    ensureHalfDayClass(start, end) {
        const className = `o_event_half_${start}_${end}`;
        if (this._halfDayStyleCache.has(className)) {
            return className;
        }

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
        let styleSheet = document.getElementById("half-day-dynamic-styles");
        if (!styleSheet) {
            styleSheet = document.createElement("style");
            styleSheet.id = "half-day-dynamic-styles";
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
        const leave = this.props.model.records[event.id];
        if (leave) {
            const isHourUnit = leave.rawRecord?.work_entry_type_request_unit === "hour";
            const leaveEnd = getLeaveLastMoment(leave);
            const isHalfStart =
                leave.requestDateFromPeriod === "pm" || (isHourUnit && leave.start.c.hour >= 12);
            const isHalfEnd =
                leave.requestDateToPeriod === "am" || (isHourUnit && leaveEnd.c.hour <= 12);
            if (!isHalfStart && !isHalfEnd) {
                return classesToAdd;
            }

            const isMultiWeek = leave.start.localWeekNumber != leaveEnd.localWeekNumber;
            let start = 0;
            let end = 100;

            if (!isMultiWeek) {
                const lastRowStart =
                    leave.start > leaveEnd.startOf("month")
                        ? leave.start
                        : leaveEnd.startOf("month");
                const firstRowEnd =
                    leaveEnd < leave.start.endOf("month") ? leaveEnd : leave.start.endOf("month");
                const daysInFirstRow =
                    firstRowEnd.startOf("day").diff(leave.start.startOf("day"), "days").days + 1;
                const daysInLastRow =
                    leaveEnd.startOf("day").diff(lastRowStart.startOf("day"), "days").days + 1;

                start = isHalfStart ? Math.round(50 / daysInFirstRow) : 0;
                end = isHalfEnd ? Math.round(100 - 50 / daysInLastRow) : 100;
            } else {
                // Multi-week: first slice — only care about start
                if (isHalfStart) {
                    const rowEnd =
                        leave.start.endOf("week") < leave.start.endOf("month")
                            ? leave.start.endOf("week").minus({ days: 1 })
                            : leave.start.endOf("month");
                    const daysInFirstRow =
                        rowEnd.startOf("day").diff(leave.start.startOf("day"), "days").days + 1;
                    start = Math.round(50 / daysInFirstRow);
                }
                // Multi-week: last slice — only care about end
                if (isHalfEnd) {
                    const rowStart =
                        leaveEnd.startOf("week") > leaveEnd.startOf("month")
                            ? leaveEnd.startOf("week").minus({ days: 1 })
                            : leaveEnd.startOf("month");
                    const daysInLastRow =
                        leaveEnd.startOf("day").diff(rowStart.startOf("day"), "days").days + 1;
                    end = Math.round(100 - 50 / daysInLastRow);
                }
            }

            classesToAdd.push(this.ensureHalfDayClass(start, end));
        }
        return classesToAdd;
    }
}
