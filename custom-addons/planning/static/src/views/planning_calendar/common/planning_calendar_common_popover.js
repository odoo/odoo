/** @odoo-module **/

import { onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";
import { formatFloatTime } from "@web/views/fields/formatters";
import { formatFloat } from "@web/core/utils/numbers";

export class PlanningCalendarCommonPopover extends CalendarCommonPopover {
    setup() {
        super.setup(...arguments);
        this.user = useService("user");

        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        this.isManager = await this.user.hasGroup("planning.group_planning_manager");
    }

    get data() {
        return this.props.record.rawRecord;
    }

    get allocatedHoursFormatted() {
        return this.data.allocated_hours && formatFloatTime(this.data.allocated_hours);
    }

    get allocatedPercentageFormatted() {
        return this.data.allocated_percentage && formatFloat(this.data.allocated_percentage);
    }

    isSet(fieldName) {
        return this.data[fieldName];
    }
}
PlanningCalendarCommonPopover.subTemplates = {
    ...CalendarCommonPopover.subTemplates,
    body: "planning.PlanningCalendarCommonPopover.body",
    footer: "planning.PlanningCalendarCommonPopover.footer",
};
