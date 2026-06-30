import { CalendarCommonPopover } from "@web/views/calendar/calendar_common/calendar_common_popover";
import { useService } from "@web/core/utils/hooks";

export class TimeOffCalendarCommonPopover extends CalendarCommonPopover {
    static template = "hr_holidays.TimeOffCalendarPopover";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.viewType = "calendar";
    }

    onEditEvent() {
        this.props.close();
        this.actionService.doAction({
            name: this.title,
            type: "ir.actions.act_window",
            res_model: this.props.model.resModel,
            res_id: this.props.record.id,
            views: [[false, "form"]],
        });
    }
}
