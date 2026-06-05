/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { CalendarController } from "@web/views/calendar/calendar_controller";

export class AttendanceCalendarController extends CalendarController {

    getQuickCreateFormViewProps(record) {
        const props = super.getQuickCreateFormViewProps(record);
        props.title = _t("Create");
        props.context.default_employee_id = this.env.searchModel.context.active_id;
        props.onRecordSaved = () => this.model.load();
        return props;
    }
}
