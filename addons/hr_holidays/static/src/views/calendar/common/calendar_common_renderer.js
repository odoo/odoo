import { onWillStart } from "@odoo/owl";
import { user } from "@web/core/user";
import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { convertRecordToEvent } from "@web/views/calendar/utils";
import { useMandatoryDays } from "../../hooks";

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
