/* @odoo-module */

import { formatFloatTime } from "@web/views/fields/formatters";
import { usePopover } from "@web/core/popover/popover_hook";

const { Component } = owl;

export class TimeOffCardPopover extends Component {}
TimeOffCardPopover.components = { Popover };

TimeOffCardPopover.template = 'hr_holidays.TimeOffCardPopover';
TimeOffCardPopover.props = ['allocated', 'approved', 'planned', 'left'];

export class TimeOffCard extends Component {
    setup() {
        this.popover = usePopover(TimeOffCardPopover, { position: "right", popoverClass: "bg-view" });
    }
    get durationFormatted() {
        return formatFloatTime(this.duration);
    }
    onClickInfo(ev) {
        const { data } = this.props;
        this.popover.open(ev.target, {
            allocated: data.max_leaves,
            approved: data.leaves_approved,
            planned: data.leaves_requested,
            left: data.virtual_remaining_leaves,
        });
    }
}

TimeOffCard.components = { TimeOffCardPopover };
TimeOffCard.template = 'hr_holidays.TimeOffCard';
TimeOffCard.props = ['name', 'id', 'data', 'requires_allocation'];

export class TimeOffCardMobile extends TimeOffCard {}

TimeOffCardMobile.template = 'hr_holidays.TimeOffCardMobile';
