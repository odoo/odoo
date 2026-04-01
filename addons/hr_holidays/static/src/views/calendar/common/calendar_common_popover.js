import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";
import { useService } from "@web/core/utils/hooks";

export class TimeOffCalendarCommonPopover extends CalendarCommonPopover {
    static subTemplates = {
        ...CalendarCommonPopover.subTemplates,
        popover: "hr_holidays.TimeOffCalendarCommonPopover.popover",
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.viewType = "calendar";
    }

    onEditEvent() {
        this.props.close()
        this.actionService.doAction({
            name: this.record.display_name,
            type: "ir.actions.act_window",
            res_model: this.props.model.resModel,
            res_id: this.record.id,
            views: [[false, "form"]],
        });
    }
}
