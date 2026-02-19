import { test, expect } from "@odoo/hoot";
import { getState } from "@hr/views/hr_employee_action_helper/hr_employee_action_helper";

test("HrEmployeeActionHelper hideHelper", () => {
    const expected = "hide";
    let isOnboarding = true;
    let hasEmployeeRights = true;
    const employees = 2;
    _testHelperState(isOnboarding, hasEmployeeRights, employees, expected);

    // Whatever the changed value, as there are employees in the view, it should still hide the helper
    isOnboarding = false;
    _testHelperState(isOnboarding, hasEmployeeRights, employees, expected);

    hasEmployeeRights = false;
    _testHelperState(isOnboarding, hasEmployeeRights, employees, expected);
});

test("HrEmployeeActionHelper onboarding", () => {
    const isOnboarding = true;
    let hasEmployeeRights = true;
    const employees = 0;
    _testHelperState(isOnboarding, hasEmployeeRights, employees, "showOnboardingLoadSample");

    hasEmployeeRights = false;
    _testHelperState(isOnboarding, hasEmployeeRights, employees, "showOnboardingMessage");
});

test("HrEmployeeActionHelper regular helper test", () => {
    const isOnboarding = false;
    let hasEmployeeRights = true;
    const employees = 0;
    _testHelperState(isOnboarding, hasEmployeeRights, employees, "showEmptyCreate");

    hasEmployeeRights = false;
    _testHelperState(isOnboarding, hasEmployeeRights, employees, "showEmpty");
});

function _testHelperState(isOnboarding, hasEmployeeRights, employeesCount, expected) {
    const helperType = isOnboarding ? "onboarding" : "regular";
    const helperState = getState(employeesCount, helperType, hasEmployeeRights);
    expect(helperState).toBe(expected, {
        message:
            `For isOnboarding: ${isOnboarding} - hasEmployeeRights: ${hasEmployeeRights} - employeesNbr: ${employeesCount} ` +
            `=====  Expected '${expected}', got '${helperState._state}'.`,
    });
}
