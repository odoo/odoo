/* @odoo-module */

import { usePopover } from "@web/core/popover/popover_hook";
import { formatNumber, useNewAllocationRequest } from "@hr_holidays/views/hooks";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillRender } from "@odoo/owl";

export class TimeOffCardPopover extends Component {
    setup() {
        this.actionService = useService("action");
    }

    async openLeaves() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "hr.leave",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: [["id", "in", this.props.errorLeaves]],
        });
    }
}

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
    "errorLeaves",
    "accrualExcess",
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
        const { data } = this.props;
        this.errorLeaves = Object.values(data.virtual_excess_data).map((data) => data.leave_id);
        this.errorLeavesDuration = Object.values(data.virtual_excess_data).reduce(
            (acc, data) => acc + data.amount,
            0
        );
        this.updateWarning();

        onWillRender(this.updateWarning);
    }

    updateWarning() {
        const { data } = this.props;
        const errorLeavesSignificant = data.allows_negative
            ? this.errorLeavesDuration > data.max_allowed_negative
            : this.errorLeavesDuration > 0;
        const accrualExcess = this.getAccrualExcess(data);
        const closeExpire =
            data.closest_allocation_duration &&
            data.closest_allocation_duration < data.virtual_remaining_leaves;
        this.warning = errorLeavesSignificant || accrualExcess || closeExpire;
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
            errorLeaves: this.errorLeaves,
            accrualExcess: this.getAccrualExcess(data),
        });
    }

    getAccrualExcess(data) {
        return data.allows_negative
            ? -data.exceeding_duration > data.max_allowed_negative
            : -data.exceeding_duration > 0;
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
