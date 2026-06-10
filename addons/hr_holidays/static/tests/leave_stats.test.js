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
            work_entry_type_id: 55,
            state: "validate",
            number_of_days: 5,
            number_of_hours: 40,
            work_entry_type_request_unit: "day",
        },
        {
            id: 13,
            employee_id: 100,
            department_id: 11,
            date_from: "2016-10-02 09:00:00",
            date_to: "2016-10-02 18:00:00",
            work_entry_type_id: 55,
            state: "validate",
            number_of_days: 1,
            number_of_hours: 8,
            work_entry_type_request_unit: "day",
        },
        {
            id: 14,
            employee_id: 200,
            department_id: 11,
            date_from: "2016-10-15 09:00:00",
            date_to: "2016-10-21 18:00:00",
            work_entry_type_id: 55,
            state: "confirm",
            number_of_days: 8,
            number_of_hours: 64,
            work_entry_type_request_unit: "day",
        },
        {
            id: 15,
            employee_id: 200,
            department_id: 11,
            date_from: "2016-10-05 10:00:00",
            date_to: "2016-10-05 11:00:00",
            work_entry_type_id: 65,
            state: "validate",
            number_of_days: 0,
            number_of_hours: 1,
            work_entry_type_request_unit: "hour",
        },
        {
            id: 16,
            employee_id: 200,
            department_id: 11,
            date_from: "2016-09-11 09:00:00",
            date_to: "2016-09-12 18:00:00",
            work_entry_type_id: 55,
            state: "validate",
            number_of_days: 2,
            number_of_hours: 16,
            work_entry_type_request_unit: "day",
        },
        {
            id: 17,
            employee_id: 100,
            department_id: 11,
            date_from: "2016-10-16 09:00:00",
            date_to: "2016-10-16 11:00:00",
            work_entry_type_id: 65,
            state: "validate",
            number_of_days: 0,
            number_of_hours: 2,
            work_entry_type_request_unit: "hour",
        },
    ];
});

test("leave stats render correctly", async () => {
    onRpc(({ method, model }) => {
        if (model === "hr.work.entry.type" && method === "get_allocation_data_request") {
            return [
                [ { id: 55, name: "Legal Leave" }, { leaves_approved: 2, max_leaves: 20, remaining_leaves: 18, unit_of_measure: "day" } ],
                [ { id: 65, name: "Unpaid Leave" }, { leaves_approved: 1, max_leaves: 5, remaining_leaves: 4, unit_of_measure: "hour" } ],
            ];
        }
        if (model === "hr.work.entry.type" && method === "search_read") {
            return [
                { id: 55, color: 1 },
                { id: 65, color: 2 }
            ];
        }
    });

    await mountView({
        type: "form",
        resModel: "hr.leave",
        resId: 14,
        arch: `
            <form string="Leave">
                <field name="employee_id"/>
                <field name="department_id"/>
                <field name="date_from"/>
                <field name="date_to"/>
                <widget name="hr_leave_stats"/>
            </form>`,
    });

    const individualLeaves = queryOne(".o_leave_stats #o_leave_stats_employee");
    const DepartmentLeaves = queryOne(".o_leave_stats #o_leave_stats_department");

    expect(individualLeaves).toBeVisible();
    expect(queryAll("div.fw-bold:contains(Legal Leave)", { root: individualLeaves })).toHaveCount(1);
    expect(queryAll("span.me-1:contains(2)", { root: individualLeaves })).toHaveCount(1);
    expect(queryAll("div.fw-bold:contains(Unpaid Leave)", { root: individualLeaves })).toHaveCount(1);
    expect(queryAll("span.me-1:contains(1)", { root: individualLeaves })).toHaveCount(1);

    // Displays all leaves for that department
    expect(DepartmentLeaves).toBeVisible();
    expect(queryAll("h4:contains(Overlaps)", { root: DepartmentLeaves })).toHaveCount(1);
    expect(queryAll("div:contains(team members on holiday during this period)", { root: DepartmentLeaves })).toHaveCount(1);
    expect(queryAll("a:contains(View Overlaps)", { root: DepartmentLeaves })).toHaveCount(1);
});

test("leave stats reload when employee/department changes", async () => {
    onRpc(({ args, kwargs, method, model }) => {
        if (model === "hr.work.entry.type" && method === "get_allocation_data_request") {
            return [];
        }
        if (model === "hr.work.entry.type" && method === "search_read") {
            return [];
        }

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
    await edit("2016-10-12 09:00");
    // Set employee => should load employee's date
    await selectFieldDropdownItem("employee_id", "Jane");
    // Set department => should load department's data
    await selectFieldDropdownItem("department_id", "R&D");
});
