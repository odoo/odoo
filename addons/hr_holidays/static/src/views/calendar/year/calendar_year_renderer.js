/** @odoo-module */

import { CalendarYearRenderer } from '@web/views/calendar/calendar_year/calendar_year_renderer';

import { useStressDays } from '../../hooks';

const { useEffect } = owl;

export class TimeOffCalendarYearRenderer extends CalendarYearRenderer {
    setup() {
        super.setup();
        this.stressDays = useStressDays(this.props);

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

    onDayRender(info) {
        super.onDayRender(info);
        this.stressDays(info);
    }
}
