import { patch } from "@web/core/utils/patch";
import { TimeOffCard, TimeOffCardPopover } from "../../../hr_holidays/static/src/dashboard/time_off_card";
import { formatNumber } from "@hr_holidays/views/hooks";
import { user } from "@web/core/user";


patch(TimeOffCardPopover.prototype, {
    props: [...TimeOffCard.props, "taken_leaves"],
    async navigateCashOutInfo(stateList) {
        const { employeeId, timeOffType, employeeCompany } = this.props;
        const isInHolidaysUserGroup = await user.hasGroup("hr_holidays.group_hr_holidays_user");

        const resModel = "hr.leave.cash.out"
        const name = "My Cash Out Requests"
        const domain = [
            ['state', 'in', stateList],
            ['leave_type_id', '=', timeOffType], ['company_id','=', employeeCompany],
            employeeId ? ['employee_id', '=', employeeId] : ['user_id', '=', user.userId]
        ];
        const context = isInHolidaysUserGroup ? {
            search_default_group_date_from: true
        } : {
            search_default_group_date_from: true,
            list_view_ref: "hr_leave_cash_out.hr_leave_cash_out_view_tree_my",
            form_view_ref: "hr_leave_cash_out.hr_leave_cash_out_view_form",
        }

        openLeaveWindow(this.actionService, resModel, name, domain, context);
    },
});

patch(TimeOffCard.prototype, {
    onClickInfo(ev) {
        const { data, holidayStatusId, employeeId } = this.props;
        this.popover.open(ev.target, {
            allocated: formatNumber(this.lang, data.max_leaves),
            accrual_bonus: formatNumber(this.lang, data.accrual_bonus),
            approved: formatNumber(this.lang, data.leaves_approved - data.cash_out_taken),
            planned: formatNumber(this.lang, data.leaves_requested - (data.virtual_cash_out_taken - data.cash_out_taken)),
            left: formatNumber(this.lang, data.virtual_remaining_leaves),
            taken_leaves: formatNumber(this.lang, data.cash_out_taken),
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
    },
});

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
