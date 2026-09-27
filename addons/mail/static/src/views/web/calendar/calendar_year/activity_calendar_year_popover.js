import { useService } from "@web/core/utils/hooks";
import { CalendarYearPopover } from "@web/views/calendar/calendar_year/calendar_year_popover";

export class ActivityCalendarYearPopover extends CalendarYearPopover {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
    }

    async onRecordClick(record) {
        const action = await this.orm.call("mail.activity", "action_open_document", [
            record.rawRecord.id,
        ]);
        this.actionService.doAction(action, { onClose: () => this.props.model.load() });
        this.props.close();
    }
}
