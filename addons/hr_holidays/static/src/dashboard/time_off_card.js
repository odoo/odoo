/* @odoo-module */

import { usePopover } from "@web/core/popover/popover_hook";
import { formatNumber, useNewAllocationRequest } from "@hr_holidays/views/hooks";
import { Component, onWillRender } from "@odoo/owl";

export class TimeOffCardPopover extends Component {}

TimeOffCardPopover.template = "hr_holidays.TimeOffCardPopover";
TimeOffCardPopover.props = [
    "allocated",
    "accrual_bonus",
    "approved",
    "planned",
    "left",
    "warning",
    "closest",
    "request_unit",
    "exceeding_duration",
    "close?",
    "allows_negative",
    "max_allowed_negative",
    "onClickNewAllocationRequest?",
];

export class TimeOffCard extends Component {
    setup() {
        this.popover = usePopover(TimeOffCardPopover, {
            position: "bottom",
            popoverClass: "bg-view",
        });
        this.newAllocationRequest = useNewAllocationRequest();
        this.lang = this.env.services.user.lang;
        this.formatNumber = formatNumber;
        this.updateWarning();

        onWillRender(this.updateWarning);
    }

    updateWarning() {
        const { data } = this.props;
        const excess = Math.max(data.exceeding_duration, -data.virtual_remaining_leaves);
        const exceeding_duration = data.allows_negative
            ? excess > data.max_allowed_negative
            : excess > 0;
        const closeExpire =
            data.closest_allocation_duration &&
            data.closest_allocation_duration < data.virtual_remaining_leaves;
        this.warning = exceeding_duration || closeExpire;
    }

    onClickInfo(ev) {
        const { data } = this.props;
        this.popover.open(ev.target, {
            allocated: formatNumber(this.lang, data.max_leaves),
            accrual_bonus: formatNumber(this.lang, data.accrual_bonus),
            approved: formatNumber(this.lang, data.leaves_approved),
            planned: formatNumber(this.lang, data.leaves_requested),
            left: formatNumber(this.lang, data.virtual_remaining_leaves),
            warning: this.warning,
            closest: data.closest_allocation_duration,
            request_unit: data.request_unit,
            exceeding_duration: data.exceeding_duration,
            allows_negative: data.allows_negative,
            max_allowed_negative: data.max_allowed_negative,
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
