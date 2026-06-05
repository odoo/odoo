import { _t } from "@web/core/l10n/translation";
import { CalendarController } from "@web/views/calendar/calendar_controller";

export class AttendanceCalendarController extends CalendarController {

    getQuickCreateFormViewProps(record) {
        const props = super.getQuickCreateFormViewProps(record);
        props.title = _t("Create");
        props.onRecordSaved = () => this.model.load();
        return props;
    }
}
