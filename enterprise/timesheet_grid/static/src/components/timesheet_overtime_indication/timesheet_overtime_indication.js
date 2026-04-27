/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { EmployeeOvertimeIndication } from "../employee_overtime_indication/employee_overtime_indication";

export class TimesheetOvertimeIndication extends EmployeeOvertimeIndication {
    static template = "timesheet_grid.TimesheetOvertimeIndication";
    static props = {
        ...EmployeeOvertimeIndication.props,
        name: String,
    };

    get shouldShowHours() {
        return super.shouldShowHours && this.props.allocated_hours > 0;
    }

    get colorClasses() {
        if (!this.shouldShowHours) {
            return "";
        }
        const progression = this.props.worked_hours / this.props.allocated_hours;
        return progression <= 0.8
            ? "text-success"
            : progression <= 0.99
            ? "text-warning"
            : "text-danger";
    }

    get overtime() {
        return this.props.allocated_hours - this.props.worked_hours;
    }

    get title() {
        if (this.props.name === "project_id") {
            return _t("Difference between the allocated %(uom)s (%(allocated_hours)s) and the %(uom)s spent (%(worked_hours)s) on the project", {
                uom: this.props.uom,
                allocated_hours: this.props.allocated_hours,
                worked_hours: this.props.worked_hours,
            });
        } else if (this.props.name === "task_id") {
            return _t("Difference between the allocated %(uom)s (%(allocated_hours)s) and the %(uom)s spent (%(worked_hours)s) on the task", {
                uom: this.props.uom,
                allocated_hours: this.props.allocated_hours,
                worked_hours: this.props.worked_hours,
            });
        } else {
            return _t("Difference between the time allocated and the time recorded");
        }
    }
}
