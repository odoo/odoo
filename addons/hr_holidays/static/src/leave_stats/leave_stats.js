/* @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useRecordObserver } from "@web/model/relational_model/utils";

import { formatDate } from "@web/core/l10n/dates";
import { Component, useState, onWillStart } from "@odoo/owl";

const { DateTime } = luxon;

export class LeaveStatsComponent extends Component {
    setup() {
        this.orm = useService("orm");

        this.state = useState({
            leaves: [],
            departmentLeaves: [],
            department: this.props.record.data.department_id,
            employee: this.props.record.data.employee_id,
        });

        this.date = this.props.record.data.date_from || DateTime.now();

        onWillStart(async () => {
            await this.loadLeaves(this.date, this.state.employee);
            await this.loadDepartmentLeaves(this.date, this.state.department, this.state.employee);
        });

        useRecordObserver(async (record) => {
            const dateFrom = record.data.date_from || DateTime.now();
            const dateChanged = this.date !== dateFrom;
            const employee = record.data.employee_id;
            const department = record.data.department_id;

            const proms = [];
            if (dateChanged || (employee && (this.state.employee && this.state.employee[0]) !== employee[0])) {
                proms.push(this.loadLeaves(dateFrom, employee));
            }

            if (
                dateChanged ||
                (department && (this.department && this.department[0]) !== department[0])
            ) {
                proms.push(this.loadDepartmentLeaves(dateFrom, department, employee));
            }
            await Promise.all(proms);

            this.date = dateFrom;
            this.state.employee = employee;
            this.state.department = department;
        });
    }

    get thisYear() {
        return this.date.toFormat("yyyy");
    }

    async loadDepartmentLeaves(date, department, employee) {
        if (!(department && employee && date)) {
            this.state.departmentLeaves = [];
            return;
        }

        const dateFrom = date.startOf("month");
        const dateTo = date.endOf("month");

        const departmentLeaves = await this.orm.searchRead(
            "hr.leave",
            [
                ["department_id", "=", department[0]],
                ["state", "=", "validate"],
                ["holiday_type", "=", "employee"],
                ["date_from", "<=", dateTo],
                ["date_to", ">=", dateFrom],
            ],
            ["employee_id", "date_from", "date_to", "number_of_days"]
        );

        this.state.departmentLeaves = departmentLeaves.map((leave) => {
            return Object.assign({}, leave, {
                dateFrom: formatDate(DateTime.fromSQL(leave.date_from, { zone: "utc" }).toLocal()),
                dateTo: formatDate(DateTime.fromSQL(leave.date_to, { zone: "utc" }).toLocal()),
                sameEmployee: leave.employee_id[0] === employee[0],
            });
        });
    }

    async loadLeaves(date, employee) {
        if (!(employee && date)) {
            this.state.leaves = [];
            return;
        }

        const dateFrom = date.startOf("year");
        const dateTo = date.endOf("year");
        this.state.leaves = await this.orm.readGroup(
            "hr.leave",
            [
                ["employee_id", "=", employee[0]],
                ["state", "=", "validate"],
                ["date_from", "<=", dateTo],
                ["date_to", ">=", dateFrom],
            ],
            ["holiday_status_id", "number_of_days:sum"],
            ["holiday_status_id"]
        );
    }
}

LeaveStatsComponent.template = "hr_holidays.LeaveStatsComponent";

export const leaveStatsComponent = {
    component: LeaveStatsComponent,
};
registry.category("view_widgets").add("hr_leave_stats", leaveStatsComponent);
