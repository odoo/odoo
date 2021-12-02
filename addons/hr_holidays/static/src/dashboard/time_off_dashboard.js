/* @odoo-module */

import { TimeOffCard } from './time_off_card';
import { DatePicker } from '@web/core/datepicker/datepicker';

const { Component } = owl;
const { DateTime } = luxon;

export class TimeOffDashboard extends Component {
    setup() {
        super.setup();
        this.yesterday = DateTime.now().minus({ days: 1 });
    }

    onDateChanged(date) {
        this.env.bus.trigger('date-changed', { date: date });
    }
}

TimeOffDashboard.components = { TimeOffCard, DatePicker };
TimeOffDashboard.template = 'hr_holidays.TimeOffDashboard';
TimeOffDashboard.props = ['holidays', 'accrual_allocations', 'date'];
