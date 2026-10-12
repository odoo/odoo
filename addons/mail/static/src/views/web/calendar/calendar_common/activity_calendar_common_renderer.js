import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";

export class ActivityCalendarCommonRenderer extends CalendarCommonRenderer {
    /**
     * @override
     * 
     * In month view, explicitly set the "dayMaxEventRows" to "true" to dynamically limit the number
     * of displayed events depending on the available day cell height.
     * Each day cell will have the same height, evenly distributed across the calendar’s total height.
     */
    get interactiveOptions() {
        return {
            ...super.interactiveOptions,
            dayMaxEventRows: this.props.model.scale === "month" || this.props.model.eventLimit,
        };
    }
}
