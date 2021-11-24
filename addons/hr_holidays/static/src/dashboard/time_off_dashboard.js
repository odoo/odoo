/* @odoo-module */

import { TimeOffCard } from './time_off_card';

export class TimeOffDashboard extends owl.Component {}

TimeOffDashboard.components = { TimeOffCard };
TimeOffDashboard.template = 'hr_holidays.TimeOffDashboard';
TimeOffDashboard.props = ['holidays'];
