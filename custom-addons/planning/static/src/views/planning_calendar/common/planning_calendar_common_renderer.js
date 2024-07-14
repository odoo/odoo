/** @odoo-module **/

import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { PlanningCalendarCommonPopover } from "@planning/views/planning_calendar/common/planning_calendar_common_popover";

export class PlanningCalendarCommonRenderer extends CalendarCommonRenderer {
    /**
     * @override
     */
    onEventRender(info) {
        super.onEventRender(info);
        const { el, event } = info;
        const model = this.props.model;
        const record = model.records[event.id];

        if (record && model.highlightIds && !model.highlightIds.includes(record.id)) {
            el.classList.add("opacity-25");
        }
    }
}
PlanningCalendarCommonRenderer.components = {
    ...CalendarCommonRenderer.components,
    Popover: PlanningCalendarCommonPopover,
};
