import { useService } from "@web/core/utils/hooks";
import { ORM } from "@web/core/orm_plugin";
import { CalendarYearPopover } from "@web/views/calendar/calendar_year/calendar_year_popover";
import { usePlugin } from "@odoo/owl";

export class ActivityCalendarYearPopover extends CalendarYearPopover {
    setup() {
        super.setup();
        this.orm = usePlugin(ORM);
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
