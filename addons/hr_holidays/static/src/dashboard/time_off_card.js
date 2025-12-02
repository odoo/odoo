import { usePopover } from "@web/core/popover/popover_hook";
import { user } from "@web/core/user";
import { formatNumber, useNewAllocationRequest } from "@hr_holidays/views/hooks";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillRender } from "@odoo/owl";

export class TimeOffCardPopover extends Component {
    static template = "hr_holidays.TimeOffCardPopover";
    static props = [
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
        "timeOffType",
        "employeeId",
        "employeeCompany",
    ];

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

    async allocatedLeaves() {
        const { employeeId, timeOffType, employeeCompany } = this.props;
        const today = new Date().toISOString().split('T')[0];
        const isInHolidaysUserGroup = await user.hasGroup("hr_holidays.group_hr_holidays_user");

        const resModel = "hr.leave.allocation"
        const name = "My Allocations"
        const context = isInHolidaysUserGroup ? {} : {
            list_view_ref: "hr_holidays.hr_leave_allocation_view_tree_my",
            form_view_ref: "hr_holidays.hr_leave_allocation_view_form",
        }
        const domain = [["holiday_status_id", "=", timeOffType], ['employee_company_id','=', employeeCompany],
                '|', ["date_to", "=", false], ["date_to", ">=", today],
                employeeId ? ['employee_id', '=', employeeId] : ['employee_id.user_id', '=', user.userId]]

        openLeaveWindow(this.actionService, resModel, name, domain, context);
    }

    async navigateInfo(stateList) {
        const { employeeId, timeOffType, employeeCompany } = this.props;
        const isInHolidaysUserGroup = await user.hasGroup("hr_holidays.group_hr_holidays_user");

        const resModel = "hr.leave"
        const name = "My Time Off"
        const domain = [
            ['state', 'in', stateList],
            ['holiday_status_id', '=', timeOffType], ['company_id','=', employeeCompany],
            employeeId ? ['employee_id', '=', employeeId] : ['user_id', '=', user.userId]
        ];
        const context = isInHolidaysUserGroup ? {
            search_default_group_date_from: true
        } : {
            search_default_group_date_from: true,
            list_view_ref: "hr_holidays.hr_leave_view_tree_my",
            form_view_ref: "hr_holidays.hr_leave_view_form",
        }

        openLeaveWindow(this.actionService, resModel, name, domain, context);
    }
}

export class TimeOffCard extends Component {
    static template = "hr_holidays.TimeOffCard";
    static props = ["name", "data", "requires_allocation", "employeeId", "holidayStatusId"];

    setup() {
        this.popover = usePopover(TimeOffCardPopover, {
            position: "bottom",
            popoverClass: "bg-view",
        });
        this.newAllocationRequest = useNewAllocationRequest();
        this.actionService = useService("action");
        this.lang = user.lang;
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
        const { data, holidayStatusId, employeeId } = this.props;
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
            timeOffType: holidayStatusId,
            employeeId: employeeId,
            employeeCompany: data.employee_company
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

    async navigateTimeOffType() {
        const { employeeId, holidayStatusId, data } = this.props;
        const isInHolidaysUserGroup = await user.hasGroup("hr_holidays.group_hr_holidays_user");

        const resModel = "hr.leave"
        const name = "My Time Off"
        const domain = [
            ['holiday_status_id', '=', holidayStatusId], ['company_id','=', data.employee_company],
            employeeId ? ['employee_id', '=', employeeId] : ['user_id', '=', user.userId]
        ];
        const context = isInHolidaysUserGroup ? {
            search_default_group_date_from: true
        } : {
            list_view_ref: "hr_holidays.hr_leave_view_tree_my",
            form_view_ref: "hr_holidays.hr_leave_view_form",
            search_default_group_date_from: true
        };

        openLeaveWindow(this.actionService, resModel, name, domain, context);
    }
}

function openLeaveWindow(actionService, resModel, name, domain, context) {
    actionService.doAction({
        type: "ir.actions.act_window",
        name: name,
        res_model: resModel,
        views: [
            [false, "list"],
            [false, "form"]
        ],
        domain: domain,
        context: context
    });
}

export class TimeOffCardMobile extends TimeOffCard {
    static template = "hr_holidays.TimeOffCardMobile";
}
