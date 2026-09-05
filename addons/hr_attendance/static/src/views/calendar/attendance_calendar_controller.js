import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { CalendarController } from "@web/views/calendar/calendar_controller";
import { onWillStart } from "@odoo/owl";

export class AttendanceCalendarController extends CalendarController {

    setup() {
        super.setup();
        onWillStart(async () => {
            const [readUser] = await this.orm.read("res.users", [user.userId], ["employee_id"]);
            if (!readUser.employee_id) {
                this.env.services.notification.add(
                    _t("You are not linked to an employee in the current company, so you cannot view your own attendances."),
                    { type: "warning" }
                );
            }
        });
    }

    get editRecordDefaultDisplayText() {
        return _t("New Attendance");
    }

    getQuickCreateFormViewProps(record) {
        const props = super.getQuickCreateFormViewProps(record);
        props.title = _t("Create");
        props.onRecordSaved = () => this.model.load();
        return props;
    }
}
