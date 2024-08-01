import { CalendarFilterPanel } from "@web/views/calendar/filter_panel/calendar_filter_panel";
import { useService } from "@web/core/utils/hooks";

export class AttendeeCalendarFilterPanel extends CalendarFilterPanel {
    static template = "calendar.AttendeeCalendarFilterPanel";

    setup() {
        super.setup();
        this.actionService = useService("action");
    }

    onClickAddCalendar() {
        this.actionService.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "calendar.add.calendar",
                views: [[false, "form"]],
                target: "new",
            },
            {
                additionalContext: this.props.context,
            }
        );
    }
}
