/** @odoo-module */

import { CalendarYearRenderer } from '@web/views/calendar/calendar_year/calendar_year_renderer';

import { useService } from "@web/core/utils/hooks";
import { useStressDays } from '../../hooks';
import { useCalendarPopover } from '@web/views/calendar/hooks';
import { TimeOffCalendarYearPopover } from './calendar_year_popover';

const { useEffect } = owl;

export class TimeOffCalendarYearRenderer extends CalendarYearRenderer {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.stressDays = useStressDays(this.props);
        this.stressDaysList = [];
        this.stressDayPopover = useCalendarPopover(TimeOffCalendarYearPopover);

        useEffect((el) => {
            for (const week of el) {
                const row = week.parentElement;

                // Remove the week number if the week is empty.
                // FullCalendar always displays 6 weeks even when empty.
                if (!row.children[1].classList.length &&
                    !row.children[row.children.length - 1].classList.length) {
                    row.remove();
                }
            }
        }, () => [this.rootRef.el && this.rootRef.el.querySelectorAll('.fc-content-skeleton td.fc-week-number')]);
    }

    get options() {
        return Object.assign(super.options, {
            weekNumbers: true,
            weekNumbersWithinDays: false,
            weekLabel: this.env._t('Week'),
        });
    }

    /** @override **/
    async onDateClick(info) {
        const is_stress_day = [...info.dayEl.classList].some(elClass => elClass.startsWith('hr_stress_day_'))
        this.stressDayPopover.close();
        if (is_stress_day && !this.env.isSmall) {
            this.popover.close();
            const date = luxon.DateTime.fromISO(info.dateStr);
            const target = info.dayEl;
            const stress_days_data = await this.orm.call("hr.employee", "get_stress_days_data", [date, date]);
            stress_days_data.forEach(stress_day_data => {
                stress_day_data['start'] = luxon.DateTime.fromISO(stress_day_data['start'])
                stress_day_data['end'] = luxon.DateTime.fromISO(stress_day_data['end'])
            });
            const records = Object.values(this.props.model.records).filter((r) =>
            luxon.Interval.fromDateTimes(r.start.startOf("day"), r.end.endOf("day")).contains(date)
            );
            const props = this.getPopoverProps(date, records)
            props['records'] = stress_days_data.concat(props['records'])
            this.stressDayPopover.open(target, props, "o_cw_popover");
        }
        else {
            super.onDateClick(info);
        }
    }

    onDayRender(info) {
        super.onDayRender(info);
        this.stressDaysList = this.stressDays(info);
    }
}
