/* @odoo-module */

import { TimeOffCard } from './time_off_card';

const { Component } = owl;

export class TimeOffDashboard extends Component {}

TimeOffDashboard.components = { TimeOffCard };
TimeOffDashboard.template = 'hr_holidays.TimeOffDashboard';
TimeOffDashboard.props = ['holidays'];
