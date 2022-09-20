/* @odoo-module */

import { useService } from '@web/core/utils/hooks';
import { getLangDateFormat } from 'web.time';
import widgetRegistry from 'web.widgetRegistry';

const { Component, useState, onWillStart, onWillUpdateProps } = owl;

export class LeaveStatsComponent extends Component {
    setup() {
        this.rpc = useService('rpc');

        this.state = useState({
            leaves: [],
            departmentLeaves: [],
        });

        onWillStart(async () => {
            await this.loadLeaves(this.date, this.employee);
            await this.loadDepartmentLeaves(this.date, this.department, this.employee);
        });
        onWillUpdateProps(async (nextProps) => {
            const dateFrom = nextProps.record.data.date_from || moment();
            const dateChanged = this.date !== dateFrom;
            const employee = nextProps.record.data.employee_id.data;
            const department = nextProps.record.data.department_id.data;

            if (dateChanged || employee && (this.employee && this.employee.id) !== employee.id) {
                await this.loadLeaves(dateFrom, employee);
            }

            if (dateChanged || department && (this.department && this.department.id) !== department.id) {
                await this.loadDepartmentLeaves(dateFrom, department, employee);
            }
        })
    }

    get date() {
        return this.props.record.data.date_from || moment();
    }

    get department() {
        return this.props.record.data.department_id && this.props.record.data.department_id.data;
    }

    get employee() {
        return this.props.record.data.employee_id.data;
    }

    get thisYear() {
        return this.date.format('YYYY');
    }

    get thisMonth() {
        return this.date.format('MMMM');
    }

    async loadDepartmentLeaves(date, department, employee) {
        if (!(department && employee && date)) {
            this.state.departmentLeaves = [];
            return;
        }

        const dateFrom = date.clone().startOf('month');
        const dateTo = date.clone().endOf('month');
        const dateFormat = getLangDateFormat();

        const departmentLeaves = await this.rpc({
            model: 'hr.leave',
            method: 'search_read',
            args: [
                [
                    ['department_id', '=', department.id],
                    ['state', '=', 'validate'],
                    ['holiday_type', '=', 'employee'],
                    ['date_from', '<=', dateTo],
                    ['date_to', '>=', dateFrom],
                ],
                ['employee_id', 'date_from', 'date_to', 'number_of_days'],
            ]
        });

        this.state.departmentLeaves = departmentLeaves.map((leave) => {
            return Object.assign({}, leave, {
                dateFrom: moment(leave.date_from).format(dateFormat),
                dateTo: moment(leave.date_to).format(dateFormat),
                sameEmployee: leave.employee_id[0] === employee.id,
            });
        });
    }

    async loadLeaves(date, employee) {
        if (!(employee && date)) {
            this.state.leaves = [];
            return;
        }

        const dateFrom = date.clone().startOf('year');
        const dateTo = date.clone().endOf('year');
        this.state.leaves = await this.rpc({
            model: 'hr.leave',
            method: 'read_group',
            kwargs: {
                domain: [
                    ['employee_id', '=', employee.id],
                    ['state', '=', 'validate'],
                    ['date_from', '<=', dateTo],
                    ['date_to', '>=', dateFrom]
                ],
                fields: ['holiday_status_id', 'number_of_days:sum'],
                groupby: ['holiday_status_id'],
            }
        });
    }
}

LeaveStatsComponent.template = 'hr_holidays.LeaveStatsComponent';
widgetRegistry.add('hr_leave_stats', LeaveStatsComponent);
