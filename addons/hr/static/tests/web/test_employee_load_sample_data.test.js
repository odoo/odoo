import { test, expect } from "@odoo/hoot";
import { EmployeeOnboardingHelper } from "@hr/core/common/onboarding/employee_onboarding_helper";

test("EmployeeOnboardingHelperState test", () => {
    // Case 1: we are not on onboarding (not on the main_company)
    let stateGetter = new EmployeeOnboardingHelper(true, false);
    let result = stateGetter.getState(["Administrator"], false);
    _testHelperState(result, "notOnboarding");

    // Case 2: on onboarding, no searching filters, only administrator being displayed, sample data still haven't been loaded
    stateGetter = new EmployeeOnboardingHelper(false, false);
    result = stateGetter.getState(["Administrator"], false);
    _testHelperState(result, "showLoadSample");

    // Case 3: same as case 2, but sample data have already been loaded -> hideHelper
    stateGetter = new EmployeeOnboardingHelper(false, true);
    result = stateGetter.getState(["Administrator"], false);
    _testHelperState(result, "hideHelper");

    // Case 4: same as case 2, but there's too many employee -> hideHelper
    stateGetter = new EmployeeOnboardingHelper(false, false);
    result = stateGetter.getState(["Administrator", "Lancelot"], false);
    _testHelperState(result, "hideHelper");

    // Case 5: same as case 2, but the only employee is not the Administrator -> hideHelper
    stateGetter = new EmployeeOnboardingHelper(false, false);
    result = stateGetter.getState(["Lancelot"], false);
    _testHelperState(result, "hideHelper");

    // Case 6: same as case 2, but there are searching filters in the view -> showEmpty (show onboarding helper blocks)
    stateGetter = new EmployeeOnboardingHelper(false, false);
    result = stateGetter.getState([], true);
    _testHelperState(result, "showEmpty");

    // Case 7: on onboarding, sample data loaded, no employee -> showEmpty
    stateGetter = new EmployeeOnboardingHelper(false, true);
    result = stateGetter.getState([], false);
    _testHelperState(result, "showEmpty");
});

function _testHelperState(state, expected) {
    expect(state.notOnboarding).toBe(expected == "notOnboarding");
    expect(state.showLoadSample).toBe(expected == "showLoadSample");
    expect(state.hideHelper).toBe(expected == "hideHelper");
    expect(state.showEmpty).toBe(expected == "showEmpty");
}
