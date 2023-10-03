/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { AttendeeCalendarController } from "@calendar/views/attendee_calendar/attendee_calendar_controller"
import { serializeDate} from "@web/core/l10n/dates";

patch(AttendeeCalendarController.prototype, {
    setup() {
        super.setup()
        this.action = useService("action");
    },
    async editRecord(record, context = {}, shouldFetchFormViewId = true) {
        if (record.homeworking && 'start' in record) {
            return this.action.doAction('hr_homeworking.set_location_wizard_action',{
                name: _t("Edit Record"),
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
    createRecord(record) {
        if (record.homework) {
            return this.action.doAction('hr_homeworking.set_location_wizard_action',{
                name: _t("Create Record"),
                additionalContext: {
                    'default_date': serializeDate(record.start),
                    'dialog_size': 'medium',
                },
                onClose: async (closeInfo) => {
                    this.model.load()
                },
            });
        } else {
            return super.createRecord(record);
        }
    },
    deleteRecord(record) {
        if (record.id && record.homeworking && !record.ghostEvent) {
            this.displayDialog(ConfirmationDialog, {
                title: _t("Confirmation"),
                body: _t("Are you sure you want to delete this exception?"),
                confirm: () => {
                    this.orm.call('hr.employee.location', "unlink", [
                        record.id,
                    ]);
                    this.model.load();
                },
                cancel: () => {
                },
            });
        } else {
            super.deleteRecord(...arguments)
        }
    },
})
