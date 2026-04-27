import { Component, onWillStart } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

export class TimeOffToDeferWarning extends Component {
    static props = {};
    static template = "hr_payroll_holidays.TimeOffToDeferWarning";

    setup() {
        this.actionService = useService("action");
    }

    /** @returns {string} */
    get timeOffButtonText() {
        const [, before, inside, after] = _t(
            "You have some <button>time off</button> to defer to the next month."
        ).match(/(.*)<button>(.*)<\/button>(.*)/) ?? [
            "You have some",
            "time off",
            "to defer to the next month.",
        ];
        return { before, inside, after };
    }

    onTimeOffToDefer() {
        this.actionService.doAction("hr_payroll_holidays.hr_leave_action_open_to_defer");
    }
}

export function useTimeOffToDefer() {
    const orm = useService("orm");
    const timeOff = {};
    onWillStart(async () => {
        const result = await orm.searchCount('hr.leave', [["payslip_state", "=", "blocked"], ["state", "=", "validate"], ["employee_company_id", "in", user.context.allowed_company_ids]]);
        timeOff.hasTimeOffToDefer = result > 0;
    });
    return timeOff;
}
