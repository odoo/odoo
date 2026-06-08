import { CalendarController } from "@web/views/calendar/calendar_controller";
import { _t } from "@web/core/l10n/translation";

export class ProjectProjectCalendarController extends CalendarController {
    get editRecordDefaultDisplayText() {
        return _t("New Project");
    }
}
