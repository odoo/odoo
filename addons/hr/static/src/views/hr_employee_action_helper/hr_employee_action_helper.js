import { ActionHelper } from "@web/views/action_helper";
import { user } from "@web/core/user";
import { onWillStart, useEnv, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { HrEmployeeOnboardingHelper } from "./hr_employee_onboarding_helper_view";
import { HrEmployeeAdminOnboardingHelper } from "./hr_employee_admin_onboarding_helper_view";
import { HrEmployeeRegularHelper } from "./hr_employee_regular_helper_view";

/**
 * Either:
 * - Hide
 * - Display the onboarding helper
 * - Display the regular helper
 */
export class HrEmployeeActionHelper extends ActionHelper {
    static template = "hr.EmployeeActionHelper";
    static components = {
        HrEmployeeRegularHelper,
        HrEmployeeOnboardingHelper,
        HrEmployeeAdminOnboardingHelper,
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.getEmployeesCount = useEnv().getEmployeesCount;
        this.state = useState({ hasEmployeeRights: null, helperType: null });
        onWillStart(async () => {
            this.state.hasEmployeeRights = await this.orm.call(
                "hr.employee",
                "has_employee_create_access",
                []
            );
            const isOnboarding = await this.orm.call("hr.employee", "is_onboarding", [
                user.context.allowed_company_ids,
            ]);
            this.state.helperType = isOnboarding ? "onboarding" : "regular";
        });
    }

    get showRegularHelper() {
        return this.state.helperType == "regular";
    }

    get showOnboardingHelper() {
        return this.state.helperType == "onboarding";
    }

    get showHelper() {
        return this._getState() != "hide";
    }

    get regularHelperShowCreate() {
        return this._getState() == "showEmptyCreate";
    }

    get showOnboardingLoadSample() {
        return this._getState() == "showOnboardingLoadSample";
    }

    _getState() {
        return getState(
            this.getEmployeesCount(),
            this.state.helperType,
            this.state.hasEmployeeRights
        );
    }

    get showDefaultHelper() {
        return false;
    }
}

export function getState(employeesCount, helperType, hasEmployeeRights) {
    if (employeesCount > 0) {
        return "hide";
    }

    if (helperType == "onboarding") {
        if (hasEmployeeRights) {
            return "showOnboardingLoadSample";
        }
        return "showOnboardingMessage";
    }

    // Regular helper states
    if (hasEmployeeRights) {
        return "showEmptyCreate";
    }
    return "showEmpty";
}
