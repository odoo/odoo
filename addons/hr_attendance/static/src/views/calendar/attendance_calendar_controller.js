import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { CalendarController } from "@web/views/calendar/calendar_controller";
import { onWillStart } from "@odoo/owl";

export class AttendanceCalendarController extends CalendarController {

    setup() {
        super.setup();
        this.hasEmployee = false;
        onWillStart(async () => {
            const [readUser] = await this.orm.read("res.users", [user.userId], ["employee_id"]);
            this.hasEmployee = Boolean(readUser.employee_id);
            if (!this.hasEmployee) {
                this.env.services.notification.add(
                    _t("You are not linked to an employee in the current company, so you cannot view your own attendances."),
                    { type: "warning" }
                );
            }
        });
    }

    createRecord(record) {
        if (!this.hasEmployee) {
            this.displayDialog(AlertDialog, {
                title: _t("Error"),
                body: _t(
                    "This operation is not allowed as you are not linked to an employee in the current company."
                ),
            });
            return;
        }
        return super.createRecord(record);
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
