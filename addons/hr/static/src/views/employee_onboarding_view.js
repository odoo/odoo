import { Component } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

import { OnboardingHelperBlocks } from "./onboarding/onboarding_helper_blocks";

export class EmployeeOnboarding extends Component {
    static template = "hr.EmployeeOnboarding";
    static props = {
        showLoadSample: { type: Boolean },
    };
    static components = { OnboardingHelperBlocks };

    setup() {
        super.setup();
        this.actionService = useService("action");
    }

    get showLoadSample() {
        return this.props.showLoadSample;
    }

    loadDemoData() {
        this.actionService.doAction("hr.action_hr_employee_load_demo_data");
    }

    loadCreateEmployee() {
        this.actionService.doAction({
            name: _t("Employees"),
            res_model: "hr.employee",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
            view_mode: "form",
            target: "current",
        });
    }
}
