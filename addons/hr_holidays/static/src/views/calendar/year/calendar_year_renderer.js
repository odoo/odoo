/** @odoo-module **/

import { CalendarYearRenderer } from "@web/views/calendar/calendar_year/calendar_year_renderer";

import { useService } from "@web/core/utils/hooks";
import { useMandatoryDays } from "../../hooks";
import { useCalendarPopover } from "@web/views/calendar/hooks";
import { TimeOffCalendarYearPopover } from "./calendar_year_popover";
import { useEffect } from "@odoo/owl";

export class TimeOffCalendarYearRenderer extends CalendarYearRenderer {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.mandatoryDays = useMandatoryDays(this.props);
        this.mandatoryDaysList = [];
        this.mandatoryDayPopover = useCalendarPopover(TimeOffCalendarYearPopover);

        useEffect(
            (el) => {
                for (const lastWeek of el) {
                    // Remove the week if the week is empty.
                    // FullCalendar always displays 6 weeks even when empty.
                    if (!lastWeek.querySelector("[data-date]")) {
                        lastWeek.remove();
                    }
                }
            },
            () => [
                this.rootRef.el &&
                    this.rootRef.el.querySelectorAll(".fc-scrollgrid-sync-table tr:nth-child(6)"),
            ]
        );
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
            this.mandatoryDayPopover.open(target, props, "o_cw_popover");
        } else {
            super.onDateClick(info);
        }
    }

    getDayCellClassNames(info) {
        return [...super.getDayCellClassNames(info), ...this.mandatoryDays(info)];
    }
}
