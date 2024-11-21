/* @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useRecordObserver } from "@web/model/relational_model/utils";

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
            date: DateTime,
            department: null,
            employee: null,
            type: null,
        });

        this.state.date = this.props.record.data.date_from || DateTime.now();
        this.state.department = this.props.record.data.department_id;
        this.state.employee = this.props.record.data.employee_id;

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
            const proms = [];
            if (
                dateChanged ||
                (employee && (this.state.employee && this.state.employee[0]) !== employee[0])
            ) {
                proms.push(this.loadLeaves(dateFrom, employee));
            }
            if (
                dateChanged ||
                (department &&
                    (this.state.department && this.state.department[0]) !== department[0])
            ) {
                proms.push(this.loadDepartmentLeaves(dateFrom, department, employee));
            }
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
                ["date_from", "<=", dateTo],
                ["date_to", ">=", dateFrom],
            ],
            [
                "employee_id",
                "date_from",
                "date_to",
                "number_of_days",
                "number_of_hours",
                "leave_type_request_unit",
            ]
        );

        this.state.departmentLeaves = departmentLeaves.map((leave) => {
            const dateFormat =
                leave.leave_type_request_unit === "hour"
                    ? {
                          ...DateTime.TIME_24_SIMPLE,
                          year: "numeric",
                          month: "2-digit",
                          day: "2-digit",
                      }
                    : {
                          year: "numeric",
                          month: "2-digit",
                          day: "2-digit",
                      };
            return Object.assign({}, leave, {
                dateFrom: DateTime.fromSQL(leave.date_from, { zone: "utc" })
                    .toLocal()
                    .toLocaleString(dateFormat),
                dateTo: DateTime.fromSQL(leave.date_to, { zone: "utc" })
                    .toLocal()
                    .toLocaleString(dateFormat),
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
            [
                "holiday_status_id",
                "number_of_days",
                "number_of_hours",
                "leave_type_request_unit:array_agg",
            ],
            ["holiday_status_id"]
        );
    }
}

export const leaveStatsComponent = {
    component: LeaveStatsComponent,
};
registry.category("view_widgets").add("hr_leave_stats", leaveStatsComponent);
