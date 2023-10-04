/* @odoo-module */

import { usePopover } from "@web/core/popover/popover_hook";
import { useNewAllocationRequest } from "@hr_holidays/views/hooks";
import { Component } from "@odoo/owl";

export class TimeOffCardPopover extends Component {}

TimeOffCardPopover.template = "hr_holidays.TimeOffCardPopover";
TimeOffCardPopover.props = [
    "allocated",
    "approved",
    "planned",
    "left",
    "employeeId",
    "holidayStatusId",
    "close?",
    "onClickNewAllocationRequest?",
];

export class TimeOffCard extends Component {
    setup() {
        this.popover = usePopover(TimeOffCardPopover, {
            position: "right",
            popoverClass: "bg-view",
        });
        this.newAllocationRequest = useNewAllocationRequest();
    }

    onClickInfo(ev) {
        const { data } = this.props;
        this.popover.open(ev.target, {
            allocated: data.max_leaves,
            approved: data.leaves_approved,
            planned: data.leaves_requested,
            left: data.virtual_remaining_leaves,
            employeeId: this.props.employeeId,
            holidayStatusId: this.props.holidayStatusId,
            onClickNewAllocationRequest: this.newAllocationRequestFrom.bind(this),
        });
    }

    async newAllocationRequestFrom() {
        this.popover.close();
        await this.newAllocationRequest(this.props.employeeId, this.props.holidayStatusId);
    }
}

TimeOffCard.template = "hr_holidays.TimeOffCard";
TimeOffCard.props = ["name", "data", "requires_allocation", "employeeId", "holidayStatusId"];

export class TimeOffCardMobile extends TimeOffCard {}

TimeOffCardMobile.template = "hr_holidays.TimeOffCardMobile";
