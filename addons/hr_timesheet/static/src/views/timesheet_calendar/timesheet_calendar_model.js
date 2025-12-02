import { _t } from "@web/core/l10n/translation";

import { TimesheetCalendarMyTimesheetsModel } from "../timesheet_calendar_my_timesheets/timesheet_calendar_my_timesheets_model";

export class TimesheetCalendarModel extends TimesheetCalendarMyTimesheetsModel {
    setup(params, services) {
        super.setup(...arguments);
        this.notification = services.notification;
    }

    async multiCreateRecords(multiCreateData, dates) {
        const [section] = this.filterSections;
        if (section.filters.filter((filter) => filter.active).length === 0) {
            this.notification.add(_t("Choose an employee to create their timesheet."), {
                type: "danger",
            });
            return;
        }
        const records = await super.multiCreateRecords(multiCreateData, dates);
        if (records.length) {
            this.notification.add(_t("Timesheets successfully created"), {
                type: "success",
            });
        } else {
            this.notification.add(
                _t("Timesheets could not be created for any of the selected days"),
                {
                    type: "danger",
                }
            );
        }
        return records;
    }
}
