/** @odoo-module **/

import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { PlanningCalendarCommonPopover } from "@planning/views/planning_calendar/common/planning_calendar_common_popover";

export class PlanningCalendarCommonRenderer extends CalendarCommonRenderer {
    static components = {
        ...CalendarCommonRenderer.components,
        Popover: PlanningCalendarCommonPopover,
    };
    /**
     * @override
     */
    eventClassNames(info) {
        const classesToAdd = super.eventClassNames(info);
        const { event } = info;
        const model = this.props.model;
        const record = model.records[event.id];

        if (record && model.highlightIds && !model.highlightIds.includes(record.id)) {
            classesToAdd.push("opacity-25");
        }
        return classesToAdd;
    }
}
