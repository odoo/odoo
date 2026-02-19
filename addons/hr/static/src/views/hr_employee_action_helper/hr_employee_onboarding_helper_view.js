import { Component } from "@odoo/owl";
import { OnboardingHelperBlocks } from "../onboarding/onboarding_helper_blocks";
import { HrEmployeeRegularHelper } from "./hr_employee_regular_helper_view";

export class HrEmployeeOnboardingHelper extends Component {
    static template = "hr.EmployeeOnboardingHelper";
    static components = { OnboardingHelperBlocks, HrEmployeeRegularHelper };
    static props = {
        regularHelperShowCreate: { type: Boolean },
    };

    get regularHelperShowCreate() {
        return this.props.regularHelperShowCreate;
    }
}
