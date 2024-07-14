/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { GridController } from "@web_grid/views/grid_controller";

const { Interval } = luxon;

export class TimesheetGridController extends GridController {
    setup() {
        super.setup();
        this.notificationService = useService("notification");
    }

    async onRecordSaved(timesheet) {
        const interval = Interval.fromDateTimes(
            this.model.navigationInfo.periodStart,
            this.model.navigationInfo.periodEnd
        );
        if (!interval.contains(timesheet.data.date)) {
            this.notificationService.add(
                _t("The timesheet entry has successfully been created."),
                {
                    type: "success",
                }
            );
        } else {
            await super.onRecordSaved(timesheet);
        }
    }

    createRecord(params) {
        const context = params?.context || {};
        if (this.model.columnFieldIsDate && this.model.unavailabilityDaysPerEmployeeId) {
            const defaultFieldName = `default_${this.model.columnFieldName}`;
            let unavailabilityDays = this.model.unavailabilityDaysPerEmployeeId.false || [];
            if (
                this.model.sectionField?.name === "employee_id" &&
                "default_employee_id" in context &&
                context.default_employee_id in this.model.unavailabilityDaysPerEmployeeId
            ) {
                unavailabilityDays =
                    this.model.unavailabilityDaysPerEmployeeId[context.default_employee_id];
            }
            if (
                unavailabilityDays.length &&
                !(defaultFieldName in context) &&
                !this.model.isToday(this.model.navigationInfo.anchor)
            ) {
                const column = this.model.columnsArray.find(
                    (col) => !unavailabilityDays.includes(col.value)
                );
                if (column) {
                    context[defaultFieldName] = column.value;
                }
            }
        }
        super.createRecord({
            ...(params || {}),
            context,
        });
    }
}
