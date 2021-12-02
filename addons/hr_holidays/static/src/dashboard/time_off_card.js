/* @odoo-module */

import Popover from "web.Popover";

const { Component } = owl;

export class TimeOffCardPopover extends Component {
    get left() {
        return Number(this.props.future) + Number(this.props.left);
    }
}

TimeOffCardPopover.components = { Popover };
TimeOffCardPopover.template = 'hr_holidays.TimeOffCardPopover';
TimeOffCardPopover.props = ['allocated', 'approved', 'planned', 'left', 'future', 'show_future'];

export class TimeOffCard extends Component {
    show_remaining() {
        return this.props.requires_allocation;
    }

    get duration() {
        const duration = Number(this.props.data.additional_leaves);

        if (this.show_remaining()) {
            return duration + Number(this.props.data.virtual_remaining_leaves);
        }
        return duration + Number(this.props.data.virtual_leaves_taken);
    }
}

TimeOffCard.components = { TimeOffCardPopover };
TimeOffCard.template = 'hr_holidays.TimeOffCard';
TimeOffCard.props = ['name', 'id', 'data', 'requires_allocation'];

export class TimeOffCardMobile extends TimeOffCard {}

TimeOffCardMobile.template = 'hr_holidays.TimeOffCardMobile';
