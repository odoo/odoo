import { user } from "@web/core/user";

export async function getEmployeeHelper(orm) {
    const isMainCompany = await orm.call("hr.employee", "is_main_company", [
        user.context.allowed_company_ids,
    ]);
    const isSampleLoaded = await orm.call("hr.employee", "has_demo_data");
    return new EmployeeOnboardingHelper(!isMainCompany, isSampleLoaded);
}

export class EmployeeOnboardingHelper {
    constructor(notOnboarding, isSampleLoaded) {
        this._notOnboarding = notOnboarding;
        this._isSampleLoaded = isSampleLoaded;
    }

    /**
     * @param {Array<String>} employeeNames Names of the displayed employees (after applying search filters)
     * @param {Boolean} isSearching Wether there are active search filters or not
     * @returns {EmployeeOnboardingHelperState}
     */
    getState(employeeNames, isSearching) {
        if (this._notOnboarding) {
            return new EmployeeOnboardingHelperState("notOnboarding");
        }

        const employeeNbr = employeeNames.length;
        if (employeeNbr > 1) {
            return new EmployeeOnboardingHelperState("hide");
        }
        if (employeeNbr == 1) {
            const adminCount = employeeNames.filter(
                (employee) => employee == "Administrator"
            ).length;

            if (adminCount == 0 || this._isSampleLoaded || isSearching) {
                return new EmployeeOnboardingHelperState("hide");
            }
            return new EmployeeOnboardingHelperState("showLoadSample");
        }
        if (!this._isSampleLoaded && !isSearching) {
            return new EmployeeOnboardingHelperState("showLoadSample");
        }
        return new EmployeeOnboardingHelperState("showEmpty");
    }
}

/**
 * Class that wraps on of the following values: "notOnboarding", "showEmpty", "showLoadSample" or "hide"
 */
export class EmployeeOnboardingHelperState {
    constructor(state) {
        this._state = state;
    }

    get notOnboarding() {
        return this._state == "notOnboarding";
    }

    get showLoadSample() {
        return this._state == "showLoadSample";
    }

    get showEmpty() {
        return this._state == "showEmpty";
    }

    get hideHelper() {
        return this._state == "hide";
    }
}
