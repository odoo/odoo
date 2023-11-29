/* @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useRecordObserver } from "@web/model/relational_model/utils";

import { formatDate } from "@web/core/l10n/dates";
import { Component, useState, onWillStart } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

const { DateTime } = luxon;

export class LeaveStatsComponent extends Component {
    static template = "hr_holidays.LeaveStatsComponent";
    static props = { ...standardWidgetProps };

    setup() {
        this.orm = useService("orm");

        this.state = useState({
            leaves: [],
            departmentLeaves: [],
            multi_employee: false,
            date: DateTime,
            department: null,
            employee: null,
            type: null,
        });

        this.state.date = this.props.record.data.date_from || DateTime.now();
        this.state.department = this.props.record.data.department_id;
        this.state.employee = this.props.record.data.employee_id;
        this.state.holiday_type = this.props.record.data.holiday_type;

        onWillStart(async () => {
            await this.loadLeaves(this.state.date, this.state.employee);
            await this.loadDepartmentLeaves(
                this.state.date,
                this.state.department,
                this.state.employee
            );
        });

        useRecordObserver(async (record) => {
            const dateFrom = record.data.date_from || DateTime.now();
            const dateChanged = !this.state.date.equals(dateFrom);
            const employee = record.data.employee_id;
            const department = record.data.department_id;
            const multi_employee = record.data.multi_employee;
            const proms = [];
            if (
                multi_employee ||
                dateChanged ||
                (employee && (this.state.employee && this.state.employee[0]) !== employee[0])
            ) {
                proms.push(this.loadLeaves(dateFrom, employee));
            }
            if (
                multi_employee ||
                dateChanged ||
                (department &&
                    (this.state.department && this.state.department[0]) !== department[0])
            ) {
                proms.push(this.loadDepartmentLeaves(dateFrom, department, employee));
            }
            this.state.multi_employee = multi_employee;
            this.state.holiday_type = record.data.holiday_type;
            await Promise.all(proms);
            this.state.date = dateFrom;
            this.state.employee = employee;
            this.state.department = department;
        });
    }

    get thisYear() {
        return this.state.date.toFormat("yyyy");
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

export const leaveStatsComponent = {
    component: LeaveStatsComponent,
};
registry.category("view_widgets").add("hr_leave_stats", leaveStatsComponent);
