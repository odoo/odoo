/** @odoo-module */

import { clickSave, selectDropdownItem, editInput } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;

QUnit.module("leave stats", {
    beforeEach() {
        setupViewRegistries();

        serverData = {
            models: {
                department: {
                    fields: {
                        name: { string: "Name", type: "char" },
                    },
                    records: [{ id: 11, name: "R&D" }],
                },
                employee: {
                    fields: {
                        name: { string: "Name", type: "char" },
                        department_id: {
                            string: "Department",
                            type: "many2one",
                            relation: "department",
                        },
                    },
                    records: [
                        {
                            id: 100,
                            name: "Richard",
                            department_id: 11,
                        },
                        {
                            id: 200,
                            name: "Jesus",
                            department_id: 11,
                        },
                    ],
                },
                "hr.leave.type": {
                    fields: {
                        name: { string: "Name", type: "char" },
                    },
                    records: [
                        {
                            id: 55,
                            name: "Legal Leave",
                        },
                    ],
                },
                "hr.leave": {
                    fields: {
                        employee_id: { string: "Employee", type: "many2one", relation: "employee" },
                        department_id: {
                            string: "Department",
                            type: "many2one",
                            relation: "department",
                        },
                        date_from: { string: "From", type: "datetime" },
                        date_to: { string: "To", type: "datetime" },
                        holiday_status_id: {
                            string: "Leave type",
                            type: "many2one",
                            relation: "hr.leave.type",
                        },
                        state: { string: "State", type: "char" },
                        holiday_type: { string: "Holiday Type", type: "char" },
                        number_of_days: { string: "State", type: "integer" },
                    },
                    records: [
                        {
                            id: 12,
                            employee_id: 100,
                            department_id: 11,
                            date_from: "2016-10-20 09:00:00",
                            date_to: "2016-10-25 18:00:00",
                            holiday_status_id: 55,
                            state: "validate",
                            number_of_days: 5,
                            holiday_type: "employee",
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
                            holiday_type: "employee",
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
                            holiday_type: "employee",
                        },
                    ],
                },
            },
        };
    },
});

QUnit.test("leave stats renders correctly", async (assert) => {
    await makeView({
        serverData,
        type: "form",
        resModel: "hr.leave",
        arch: `
            <form string="Leave">
                <field name="employee_id"/>
                <field name="department_id"/>
                <field name="date_from"/>
                <widget name="hr_leave_stats"/>
            </form>`,
        resId: 12,
        async mockRPC(route, args) {
            if (args.model === "hr.leave" && args.method === "search") {
                return this.data["hr.leave"].records.map((record) => record.id);
            }
        },
    });
    const $leaveTypeBody = $(".o_leave_stats #o_leave_stats_employee");
    const $leavesDepartmentBody = $(".o_leave_stats #o_leave_stats_department");
    assert.containsOnce($leaveTypeBody, "span:contains(Legal Leave)");
    assert.containsOnce($leaveTypeBody, "span:contains(6)");
    assert.containsN($leavesDepartmentBody, "span:contains(Richard)", 2);
    assert.containsOnce($leavesDepartmentBody, "span:contains(Jesus)");
    assert.containsOnce($leavesDepartmentBody, "div.o_horizontal_separator:contains(R&D)");
});

QUnit.test("leave stats reload when employee/department changes", async (assert) => {
    assert.expect(2);
    await makeView({
        serverData,
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
        mockRPC(route, args) {
            if (args.model === "hr.leave" && args.method === "search_read") {
                assert.ok(
                    args.kwargs.domain.some(
                        (x) => JSON.stringify(x) === JSON.stringify(["department_id", "=", 11])
                    )
                );
            }
            if (args.model === "hr.leave" && args.method === "read_group") {
                assert.ok(
                    args.kwargs.domain.some(
                        (x) => JSON.stringify(x) === JSON.stringify(["employee_id", "=", 200])
                    )
                );
            }
        },
    });

    // Set date => shouldn't load data yet (no employee nor department defined)
    await editInput(document.body, "div[name='date_from'] input", "2016-10-12 09:00:00");
    // Set employee => should load employee's date
    await selectDropdownItem(document.body, "employee_id", "Jesus");
    // Set department => should load department's data
    await selectDropdownItem(document.body, "department_id", "R&D");
});

QUnit.test("leave stats renders after multi-employee", async (assert) => {
    await makeView({
        serverData,
        type: "form",
        resModel: "hr.leave",
        arch: `
            <form string="Leave">
                <field name="employee_id"/>
                <field name="department_id"/>
                <field name="date_from"/>
                <widget name="hr_leave_stats"/>
            </form>`,
        resId: 12,
    });
    
    await selectDropdownItem(document.body, "employee_id", "Jesus");
    await clickSave(document.body);

    const $leaveTypeBody = $(".o_leave_stats #o_leave_stats_employee");
    const $leavesDepartmentBody = $(".o_leave_stats #o_leave_stats_department");
    assert.containsOnce($leaveTypeBody, "span:contains(Legal Leave)");
    assert.containsOnce($leaveTypeBody, "span:contains(13)");
    assert.containsN($leavesDepartmentBody, "span:contains(Jesus)", 2);
    assert.containsOnce($leavesDepartmentBody, "span:contains(Richard)");
    assert.containsOnce($leavesDepartmentBody, "div.o_horizontal_separator:contains(R&D)");
});
