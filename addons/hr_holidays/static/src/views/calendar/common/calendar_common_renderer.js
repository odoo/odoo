import { onWillStart } from "@odoo/owl";
import { user } from "@web/core/user";
import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { convertRecordToEvent } from "@web/views/calendar/utils";
import { useMandatoryDays } from "../../hooks";

const { DateTime } = luxon;

export class TimeOffCalendarCommonRenderer extends CalendarCommonRenderer {
    setup() {
        super.setup();
        this.mandatoryDays = useMandatoryDays(this.props);
        onWillStart(async () => {
            this.isManager = await user.hasGroup("hr_holidays.group_hr_holidays_user");
        });
    }

    /**
     * @override
     * Make a leave draggable/resizable. The model re-snaps the dragged result on write,
     * so no gesture can produce a duration the leave type forbids; editing stays gated
     * by `can_reschedule` and `canEdit`. Note "half_day" snaps the endpoints to AM/PM —
     * it does not cap the leave at half a day.
     *
     * On the month grid a sub-24h (half-)day leave would map to a "timed" event
     * FullCalendar won't resize, so render it all-day there to expose its day-border.
     */
    convertRecordToEvent(record) {
        // The hr.leave.report.calendar dashboard reuses this view without these fields.
        if (this.props.model.resModel !== "hr.leave") {
            return super.convertRecordToEvent(record);
        }
        const rawRecord = record.rawRecord || {};
        const isHourUnit = rawRecord.work_entry_type_request_unit === "hour";
        const scale = this.props.model.scale;
        const isMonth = scale === "month";
        const isTimeGrid = scale === "week" || scale === "day";

        const event =
            isMonth && !isHourUnit
                ? convertRecordToEvent(record, true)
                : super.convertRecordToEvent(record);

        const allowed = this.props.model.canEdit && Boolean(rawRecord.can_reschedule);
        let movable, resizable;
        if (isHourUnit) {
            // An hour leave has no day-border to grab, so it only resizes on a time axis.
            movable = allowed;
            resizable = allowed && isTimeGrid;
        } else {
            // day / half_day leaves re-snap on write, so the time grid is safe too.
            movable = allowed;
            resizable = allowed;
        }
        return {
            ...event,
            editable: movable || resizable,
            startEditable: movable,
            durationEditable: resizable,
        };
    }

    getDayCellClassNames(info) {
        return [...super.getDayCellClassNames(info), ...this.mandatoryDays(info)];
    }

    onClick(info) {
        // To open record view
        return this.onDblClick(info);
    }
}

/**
 * Draws a month of one employee as their working days: a day is a working day high, a time off as high as the
 * share of it that `getDayShare(record)` gives, an afternoon at the bottom of its day.
 */
export class TimeOffWorkingDaysCommonRenderer extends TimeOffCalendarCommonRenderer {
    /**
     * @override
     */
    get options() {
        return this.showsWorkingDays()
            ? { ...super.options, eventOrder: "order", viewClass: "o_working_day_calendar" }
            : super.options;
    }

    showsWorkingDays() {
        return this.props.model.scale === "month" && !this.uiService.isSmall;
    }

    /** A time off of several days is as high as its fullest day, a whole one. */
    getDayShare(record) {
        return Math.min(1, record.rawRecord.number_of_days);
    }

    /**
     * @override
     */
    mapRecordsToEvents() {
        const events = super.mapRecordsToEvents();
        if (!this.showsWorkingDays()) {
            return events;
        }
        const { records } = this.props.model;
        const minutes = ({ start }) => start.hour * 60 + start.minute;
        // How far down each day is filled: FullCalendar stacks the time off in the order they fill it.
        const filled = {};
        return events
            .map((event) => [event, records[event.id]])
            .sort(
                ([, a], [, b]) =>
                    minutes(a) - minutes(b) ||
                    a.start - b.start ||
                    b.end - b.start - (a.end - a.start) ||
                    String(a.id).localeCompare(String(b.id))
            )
            .map(([event, record], order) => {
                const share = this.getDayShare(record);
                const days = [];
                for (let day = record.start.startOf("day"); day <= DateTime.max(record.start, record.end.minus(1)); day = day.plus({ days: 1 })) {
                    days.push(day.toISODate());
                }
                const top = Math.max(...days.map((day) => filled[day] || 0));
                // An afternoon ends its day, even with nothing in the morning above it.
                const offset = days.length === 1 && record.start.hour >= 12 ? Math.max(0, 1 - share - top) : 0;
                for (const day of days) {
                    filled[day] = top + offset + share;
                }
                return { ...event, order, share, offset };
            });
    }

    /**
     * @override
     * Its height tells its hours: a timed time off is a block like the others.
     */
    eventClassNames() {
        const classNames = super.eventClassNames(...arguments);
        return this.showsWorkingDays() ? classNames.filter((className) => className !== "o_event_dot") : classNames;
    }

    /**
     * @override
     */
    onEventDidMount({ el, event }) {
        super.onEventDidMount(...arguments);
        if (this.showsWorkingDays()) {
            el.style.setProperty("--o-working-day__share", event.extendedProps.share);
            el.style.setProperty("--o-working-day__offset", event.extendedProps.offset);
        }
    }
}
