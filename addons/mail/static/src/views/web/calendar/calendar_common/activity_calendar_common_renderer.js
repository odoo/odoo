import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { ActivityCalendarCommonPopover } from "./activity_calendar_common_popover";

export class ActivityCalendarCommonRender extends CalendarCommonRenderer {
    static components = {
        ...CalendarCommonRenderer.components,
        Popover: ActivityCalendarCommonPopover,
    };

    /**
     * @override
     * 
     * In month view, do not limit the number of displayed events using a fixed event limit.
     * Instead, explicitly set the "dayMaxEventRows" to "true" to dynamically limit the number
     * of displayed events depending on the available day cell height.
     * Each day cell will have the same height, evenly distributed across the calendar’s total height.
     */
    get interactiveOptions() {
        return {
            ...super.interactiveOptions,
            dayMaxEventRows: this.props.model.scale === "month" ? true : this.props.model.eventLimit,
        };
    }
}
