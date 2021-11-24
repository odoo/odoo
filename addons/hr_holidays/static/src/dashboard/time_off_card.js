/* @odoo-module */

export class TimeOffCardPopover extends owl.Component {}

TimeOffCardPopover.template = 'hr_holidays.TimeOffCardPopover';
TimeOffCardPopover.props = ['allocated', 'approved', 'planned', 'left'];

export class TimeOffCard extends owl.Component {}

TimeOffCard.components = { TimeOffCardPopover };
TimeOffCard.template = 'hr_holidays.TimeOffCard';
TimeOffCard.props = ['name', 'id', 'data', 'requires_allocation'];

export class TimeOffCardMobile extends TimeOffCard {}

TimeOffCardMobile.template = 'hr_holidays.TimeOffCardMobile';
