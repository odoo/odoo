import { describe, test, expect, beforeEach } from "@odoo/hoot";
import { click, edit, queryAll, queryOne } from "@odoo/hoot-dom";
import { mountView, onRpc, selectFieldDropdownItem } from "@web/../tests/web_test_helpers";
import { defineHrHolidaysModels } from "@hr_holidays/../tests/hr_holidays_test_helpers";
import { HrLeave } from "@hr_holidays/../tests/mock_server/mock_models/hr_leave";
import { mockTimeZone } from "@odoo/hoot-mock";

describe.current.tags("desktop");
defineHrHolidaysModels();

beforeEach(() => {
    mockTimeZone("Europe/Brussels");
    HrLeave._records = [
        {
            id: 12,
            employee_id: 100,
            department_id: 11,
            date_from: "2016-10-20 09:00:00",
            date_to: "2016-10-25 18:00:00",
            holiday_status_id: 55,
            state: "validate",
            number_of_days: 5,
            number_of_hours: 40,
            leave_type_request_unit: "day",
        },
        {
            id: 13,
            employee_id: 100,
            department_id: 11,
            date_from: "2016-10-02 09:00:00",
            date_to: "2016-10-02 18:00:00",
            holiday_status_id: 55,
            state: "validate",
            number_of_days: 1,
            number_of_hours: 8,
            leave_type_request_unit: "day",
        },
        {
            id: 14,
            employee_id: 200,
            department_id: 11,
            date_from: "2016-10-15 09:00:00",
            date_to: "2016-10-20 18:00:00",
            holiday_status_id: 55,
            state: "validate",
            number_of_days: 8,
            number_of_hours: 64,
            leave_type_request_unit: "day",
        },
        {
            id: 15,
            employee_id: 200,
            department_id: 11,
            date_from: "2016-10-05 10:00:00",
            date_to: "2016-10-05 11:00:00",
            holiday_status_id: 65,
            state: "validate",
            number_of_days: 0,
            number_of_hours: 1,
            leave_type_request_unit: "hour",
        },
    ];
});

test("leave stats render correctly", async () => {
    await mountView({
        type: "form",
        resModel: "hr.leave",
        resId: 15,
        arch: `
            <form string="Leave">
                <field name="employee_id" eval="100"/>
                <field name="department_id" eval="11"/>
                <field name="date_from"/>
                <widget name="hr_leave_stats"/>
            </form>`,
    });

    const individualLeaves = queryOne(".o_leave_stats #o_leave_stats_employee");
    const DepartmentLeaves = queryOne(".o_leave_stats #o_leave_stats_department");
    // Displays leaves with the correct unit
    expect(queryAll("span:contains(Legal Leave)", { root: individualLeaves })).toHaveCount(1);
    expect(queryAll("span:contains(8 day(s))", { root: individualLeaves })).toHaveCount(1);
    expect(queryAll("span:contains(Unpaid Leave)", { root: individualLeaves })).toHaveCount(1);
    // The test below can be uncommented once array_agg is implemented in the mock server.
    // expect(queryAll("span:contains(1 hour(s))", { root: individualLeaves })).toHaveCount(1);

    // Displays all leaves for that department
    expect(queryAll("span:contains(Richard)", { root: DepartmentLeaves })).toHaveCount(2);
    expect(queryAll("span:contains(Jane)", { root: DepartmentLeaves })).toHaveCount(2);
    expect(queryAll("span:contains(10/15/2016)", { root: DepartmentLeaves })).toHaveCount(1);
    expect(queryAll("span:contains(10/05/2016, 12:00)", { root: DepartmentLeaves })).toHaveCount(1);

    expect(
        queryAll("div.o_horizontal_separator:contains(R&D)", { root: DepartmentLeaves })
    ).toHaveCount(1);
});

test("leave stats reload when employee/department changes", async () => {
    onRpc(({ args, kwargs, method, model }) => {
        if (
            model === "hr.leave" &&
            method === "search_read" &&
            kwargs.domain[0][0] === "department_id"
        ) {
            expect(
                kwargs.domain.some(
                    (x) => JSON.stringify(x) === JSON.stringify(["department_id", "=", 11])
                )
            ).toBe(true);
        }
        if (
            model === "hr.leave" &&
            method === "search_read" &&
            kwargs.domain[0][0] === "employee_id"
        ) {
            expect(
                kwargs.domain.some(
                    (x) => JSON.stringify(x) === JSON.stringify(["employee_id", "=", 200])
                )
            ).toBe(true);
        }
    });
    await mountView({
        type: "form",
        resModel: "hr.leave",
        mode: "edit",
        arch: `
            <form string="Leave">
                <field name="employee_id"/>
                <field name="department_id"/>
                <field name="date_from"/>
                <widget name="hr_leave_stats"/>
            </form>`,
    });

    // Set date => shouldn't load data yet (no employee nor department defined)
    await click("div[name='date_from'] input");
    await edit("2016-10-12 09:00:00");
    // Set employee => should load employee's date
    await selectFieldDropdownItem("employee_id", "Jane");
    // Set department => should load department's data
    await selectFieldDropdownItem("department_id", "R&D");
});
