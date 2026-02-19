import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { OnboardingHelperBlocks } from "@hr/views/onboarding/onboarding_helper_blocks";

export class HrEmployeeAdminOnboardingHelper extends Component {
    static template = "hr.EmployeeAdminOnboardingHelper";
    static components = { OnboardingHelperBlocks };
    static props = {};

    setup() {
        super.setup();
        this._actionService = useService("action");
    }

    loadDemoData() {
        this._actionService.doAction("hr.action_hr_employee_load_demo_data");
    }

    loadNewEmployeeForm() {
        this._actionService.doAction({
            name: _t("Employees"),
            res_model: "hr.employee",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
            view_mode: "form",
            target: "current",
        });
    }
}
