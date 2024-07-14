/** @odoo-module */

import { deserializeDate } from "@web/core/l10n/dates";
import { GridRenderer } from "@web_grid/views/grid_renderer";
import { onWillStart } from "@odoo/owl";

export class TimesheetGridRenderer extends GridRenderer {
    static components = {
        ...GridRenderer.components,
    };

    setup() {
        super.setup();
        onWillStart(this.onWillStart);
    }

    async onWillStart() {
        await this._fetchLastValidatedTimesheetDate();
    }

    async onWillUpdateProps(nextProps) {
        if (this.lastValidationDatePerEmployee === undefined) {
            await this._fetchLastValidatedTimesheetDate(nextProps);
        }
    }

    getUnavailableClass(column, cellData = {}) {
        if (!this.props.model.unavailabilityDaysPerEmployeeId) {
            return "";
        }
        const unavailabilityClass = "o_grid_unavailable";
        let employee_id = false;
        if (cellData.section && this.props.model.sectionField?.name === "employee_id") {
            employee_id = cellData.section.value && cellData.section.value[0];
        } else if (cellData.row && "employee_id" in cellData.row.valuePerFieldName) {
            employee_id =
                cellData.row.valuePerFieldName.employee_id &&
                cellData.row.valuePerFieldName.employee_id[0];
        }
        const unavailabilityDays = this.props.model.unavailabilityDaysPerEmployeeId[employee_id];
        return unavailabilityDays && unavailabilityDays.includes(column.value)
            ? unavailabilityClass
            : "";
    }

    getFieldAdditionalProps(fieldName) {
        const props = super.getFieldAdditionalProps(fieldName);
        if (fieldName in this.props.model.workingHoursData) {
            props.workingHours = this.props.model.workingHoursData[fieldName];
        }
        return props;
    }

    async _fetchLastValidatedTimesheetDate(props = this.props) {
        if (!props.model.useSampleModel) {
            await this._getLastValidatedTimesheetDate(props);
        }
    }

    async _getLastValidatedTimesheetDate(props = this.props) {
        this.lastValidationDatePerEmployee = {};
        if (props.sectionField?.name === 'employee_id') {
            const employeeIds = props.model._dataPoint._getFieldValuesInSectionAndRows(props.model.fieldsInfo.employee_id);
            if (employeeIds.length) {
                const result = await props.model.orm.call(
                    "hr.employee",
                    "get_last_validated_timesheet_date",
                    [employeeIds],
                );
                for (const [employee_id, last_validated_timesheet_date] of Object.entries(result)) {
                    this.lastValidationDatePerEmployee[employee_id] = last_validated_timesheet_date && deserializeDate(last_validated_timesheet_date);
                }
            }
        }
    }

    get displayAddLine() {
        const res = super.displayAddLine;
        if (!res || this.props.sectionField?.name !== "employee_id") {
            return res;
        }

        const employeeId = this.row.section.valuePerFieldName.employee_id[0];
        if (employeeId in this.lastValidationDatePerEmployee) {
            return res && (!this.lastValidationDatePerEmployee[employeeId] || this.lastValidationDatePerEmployee[employeeId].startOf("day") < this.props.model.navigationInfo.periodEnd.startOf("day"));
        }

        return res;
    }
}
