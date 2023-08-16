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
        if ('rawRecord' in record && 'date' in record.rawRecord) {
            return this.action.doAction('hr_homeworking.hr_employee_location_action',{
                name: _t("Edit Record"),
                additionalContext: {
                    'default_start_date': serializeDate(record.start),
                    'default_end_date_create': serializeDate(record.end),
                    'default_work_location_id' : record.rawRecord.location_id,
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
            return this.action.doAction('hr_homeworking.hr_employee_location_action',{
                name: _t("Create Record"),
                additionalContext: {
                    'default_start_date': serializeDate(record.start),
                    'default_end_date_create': serializeDate(record.start),
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
        if ('rawRecord' in record && 'date' in record.rawRecord) {
            if (record.rawRecord.weekly) {
                this.openRecurringDeletionWizardForHomework(record);
            } else {
                this.displayDialog(ConfirmationDialog, {
                    title: _t("Confirmation"),
                    body: _t("Are you sure you want to delete this work location?"),
                    confirm: () => {
                        this.orm.call('hr.employee.location', "unlink", [
                            record.rawRecord.idInDB,
                        ]);
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

    openRecurringDeletionWizardForHomework(record) {
        this.action.doAction('hr_homeworking.hr_popover_delete_homework_action',{
            additionalContext: {
                'default_hr_employee_location_id': record.rawRecord.idInDB,
                'default_start_date': serializeDate(record.start)
            },
            onClose: async (closeInfo) => {
                this.model.load()
            },
        });
    }
})
