/* @odoo-module */

import { useService } from '@web/core/utils/hooks';
import { registry } from '@web/core/registry'

import { formatDate } from "@web/core/l10n/dates";

const { Component, useState, onWillStart, onWillUpdateProps } = owl;
const { DateTime } = luxon;

export class LeaveStatsComponent extends Component {
    setup() {
        this.orm = useService('orm');

        this.state = useState({
            leaves: [],
            departmentLeaves: [],
        });

        this.date = this.props.record.data.date_from || DateTime.now();
        this.department = this.props.record.data.department_id;
        this.employee = this.props.record.data.employee_id;

        onWillStart(async () => {
            await this.loadLeaves(this.date, this.employee);
            await this.loadDepartmentLeaves(this.date, this.department, this.employee);
        });
        onWillUpdateProps(async (nextProps) => {
            const dateFrom = nextProps.record.data.date_from || DateTime.now();
            const dateChanged = this.date !== dateFrom;
            const employee = nextProps.record.data.employee_id;
            const department = nextProps.record.data.department_id;

            if (dateChanged || employee && (this.employee && this.employee[0]) !== employee[0]) {
                await this.loadLeaves(dateFrom, employee);
            }

            if (dateChanged || department && (this.department && this.department[0]) !== department[0]) {
                await this.loadDepartmentLeaves(dateFrom, department, employee);
            }

            this.date = dateFrom;
            this.employee = employee;
            this.department = department;
        })
    }

    get thisYear() {
        return this.date.toFormat('yyyy');
    }

    async loadDepartmentLeaves(date, department, employee) {
        if (!(department && employee && date)) {
            this.state.departmentLeaves = [];
            return;
        }

        const dateFrom = date.startOf('month');
        const dateTo = date.endOf('month');

        const departmentLeaves = await this.orm.searchRead(
            'hr.leave',
            [
                ['department_id', '=', department[0]],
                ['state', '=', 'validate'],
                ['holiday_type', '=', 'employee'],
                ['date_from', '<=', dateTo],
                ['date_to', '>=', dateFrom],
            ],
            ['employee_id', 'date_from', 'date_to', 'number_of_days'],
        );

        this.state.departmentLeaves = departmentLeaves.map((leave) => {
            return Object.assign({}, leave, {
                dateFrom: formatDate(DateTime.fromSQL(leave.date_from, { zone: 'utc' }).toLocal()),
                dateTo: formatDate(DateTime.fromSQL(leave.date_to, { zone: 'utc' }).toLocal()),
                sameEmployee: leave.employee_id[0] === employee[0],
            });
        });
    }

    async loadLeaves(date, employee) {
        if (!(employee && date)) {
            this.state.leaves = [];
            return;
        }

        const dateFrom = date.startOf('year');
        const dateTo = date.endOf('year');
        this.state.leaves = await this.orm.readGroup(
            'hr.leave',
            [
                ['employee_id', '=', employee[0]],
                ['state', '=', 'validate'],
                ['date_from', '<=', dateTo],
                ['date_to', '>=', dateFrom]
            ],
            ['holiday_status_id', 'number_of_days:sum'],
            ['holiday_status_id'],
        );
    }
}

LeaveStatsComponent.template = 'hr_holidays.LeaveStatsComponent';
registry.category('view_widgets').add('hr_leave_stats', LeaveStatsComponent);
