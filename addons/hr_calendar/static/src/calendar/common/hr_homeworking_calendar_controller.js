import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { AttendeeCalendarController } from "@calendar/views/attendee_calendar/attendee_calendar_controller"
import { serializeDate} from "@web/core/l10n/dates";
import { user } from "@web/core/user";
import { onWillStart } from "@odoo/owl";

patch(AttendeeCalendarController.prototype, {
    setup() {
        super.setup();
        this.action = useService("action");
        this._baseRendererProps.openWorkLocationWizard = this.openWorkLocationWizard.bind(this);
        this.canLinkEmployee = false;
        onWillStart(async () => {
            this.canLinkEmployee = await user.hasGroup("hr.group_hr_user");
        });
    },
    async editRecord(record) {
        if (record.homeworking && 'start' in record) {
            return this.action.doAction('hr_calendar.set_location_wizard_action', {
                additionalContext: {
                    'default_date': serializeDate(record.start),
                    'default_work_location_id' : record.work_location_id,
                    'dialog_size': 'medium',
                },
                onClose: async (closeInfo) => {
                    this.model.load()
                },
            });
        }
        return super.editRecord(...arguments)
    },
    deleteRecord(record) {
        if (record.id && record.homeworking) {
            if (record.ghostRecord) {
                this.displayDialog(ConfirmationDialog, {
                    title: _t("Confirmation"),
                    body: _t("Are you sure you want to delete this location?"),
                    confirm: async () => {
                        const dayName = record.start.setLocale("en").weekdayLong.toLowerCase();
                        const locationField = `${dayName}_location_id`;
                        await this.orm.write('res.users', [record.rawRecord.user_id], {[locationField]: false})
                        this.model.load();
                    },
                    cancel: () => {
                    },
                });
            } else {
                this.displayDialog(ConfirmationDialog, {
                    title: _t("Confirmation"),
                    body: _t("Are you sure you want to delete this exception?"),
                    confirm: async () => {
                        await this.orm.unlink("hr.employee.location", [parseInt(record.id)]);
                        this.model.load();
                    },
                    cancel: () => {
                    },
                });
            }
        } else {
            super.deleteRecord(...arguments)
        }
    },
    async openWorkLocationWizard(startDate, locationId = undefined, ghostRecord= undefined) {
        const [employeeRecord] = await this.orm.read("res.users", [user.userId], ["employee_id"]);
        if (!employeeRecord.employee_id) {
            this.displayDialog(ConfirmationDialog, {
                title: _t("Missing Employee"),
                body: _t("An administrator first needs to link your user to an employee in order to set work locations."),
                confirm: this.canLinkEmployee ? () => this.action.doAction({
                        type: "ir.actions.act_window",
                        res_model: "hr.employee",
                        views: [[false, "kanban"]],
                    }) : () => {},
                confirmLabel: this.canLinkEmployee ? _t("Link Employee") : _t("Ok"),
                cancel: this.canLinkEmployee ? () => {} : undefined,  // Provide explicit cancel button
                cancelLabel: this.canLinkEmployee ? _t("Close") : undefined
            });
            return;
        }

        this.action.doAction('hr_calendar.set_location_wizard_action',{
            additionalContext: {
                'default_date': serializeDate(startDate),
                'default_work_location_id': locationId,
                'dialog_size': 'medium',
                'default_weekly': !!ghostRecord,
            },
            onClose: async () => {
                this.model.load()
            },
        })
    },
})
