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

    /**
     * @override
     */
    eventClassNames({ event }) {
        const classesToAdd = super.eventClassNames(...arguments);
        const record = this.props.model.records[event.id];
        if (record && record.requestDateFromPeriod && record.sameDay) {
            if (record.requestDateFromPeriod === "am" && record.requestDateToPeriod === "am") {
                classesToAdd.push("o_event_half_left")
            } else if (record.requestDateFromPeriod === "pm" && record.requestDateToPeriod === "pm") {
                classesToAdd.push("o_event_half_right")
            }
        }
        // handling half pill UX for custom_hours
        if (record?.rawRecord?.request_unit_hours && record.sameDay) {
            if (record.end.c.hour < 12) {
                classesToAdd.push("o_event_half_left");
            } else if (record.end.c.hour >= 12) {
                classesToAdd.push("o_event_half_right");
            }
        }
        return classesToAdd;
    }
}
