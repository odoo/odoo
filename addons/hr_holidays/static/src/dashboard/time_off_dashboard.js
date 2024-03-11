/* @odoo-module */

import { TimeOffCard } from './time_off_card';
import { useBus, useService } from "@web/core/utils/hooks";

const { Component, useState, onWillStart } = owl;

export class TimeOffDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            holidays: [],
        });
        useBus(this.env.timeOffBus, 'update_dashboard', async () => {
            await this.loadDashboardData()
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }
    
    async loadDashboardData() {
        const context = {};
        if (this.props.employeeId !== null) {
            context['employee_id'] = this.props.employeeId;
        }

        this.state.holidays = await this.orm.call(
            'hr.leave.type',
            'get_days_all_request',
            [],
            {
                context: context
            }
        );
    }
}

TimeOffDashboard.components = { TimeOffCard };
TimeOffDashboard.template = 'hr_holidays.TimeOffDashboard';
TimeOffDashboard.props = ['employeeId'];
