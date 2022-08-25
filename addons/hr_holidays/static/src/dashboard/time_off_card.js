/* @odoo-module */

import Popover from "web.Popover";

const { Component } = owl;

export class TimeOffCardPopover extends Component {}
TimeOffCardPopover.components = { Popover };

TimeOffCardPopover.template = 'hr_holidays.TimeOffCardPopover';
TimeOffCardPopover.props = ['allocated', 'approved', 'planned', 'left'];

export class TimeOffCard extends Component {}

TimeOffCard.components = { TimeOffCardPopover };
TimeOffCard.template = 'hr_holidays.TimeOffCard';
TimeOffCard.props = ['name', 'id', 'data', 'requires_allocation'];

export class TimeOffCardMobile extends TimeOffCard {}

TimeOffCardMobile.template = 'hr_holidays.TimeOffCardMobile';
