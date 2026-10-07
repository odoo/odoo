import { createPublicEmployee, hrModels } from "@hr/../tests/hr_test_helpers";
import { HrEmployee } from "@hr/../tests/mock_server/mock_models/hr_employee";
import { describe, expect, test } from "@odoo/hoot";
import { runAllTimers } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    fields,
    makeMockServer,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

class CalendarEmployeeEvent extends models.Model {
    _name = "calendar.employee.event";

    name = fields.Char();
    start = fields.Datetime();
    employee_id = fields.Many2one({ string: "Employee", relation: "hr.employee" });
}

class CalendarEmployeeFilter extends models.Model {
    _name = "calendar.employee.filter";

    user_id = fields.Many2one({ relation: "res.users" });
    employee_id = fields.Many2one({ relation: "hr.employee" });
    checked = fields.Boolean();
}

defineModels({ ...hrModels, CalendarEmployeeEvent, CalendarEmployeeFilter });

async function openSearchMoreDialog() {
    const { env } = await makeMockServer();
    createPublicEmployee(
        env,
        [...Array(9).keys()].map((index) => ({ name: `Employee ${index + 1}` }))
    );
    await mountView({
        resModel: "calendar.employee.event",
        type: "calendar",
        arch: `
            <calendar date_start="start">
                <field name="employee_id" write_model="calendar.employee.filter" write_field="employee_id" filter_field="checked"/>
            </calendar>
        `,
    });
    await contains(`.o_calendar_filter[data-name="employee_id"] .o-autocomplete--input`).click();
    await runAllTimers();
    await contains(".o-autocomplete--dropdown-item:contains(Search More...)").click();
}

test("calendar filter search more opens public employees without hr access", async () => {
    onRpc("has_group", () => false);
    onRpc("web_search_read", ({ model }) => {
        expect.step(model);
    });
    await openSearchMoreDialog();
    expect(".modal .o_data_row").toHaveCount(9);
    expect.verifySteps(["hr.employee.public"]);
});

test("calendar filter search more opens employees with hr access", async () => {
    HrEmployee._views = {
        search: `<search><field name="name"/></search>`,
        list: `<list><field name="name"/></list>`,
    };
    onRpc("has_group", () => true);
    onRpc("web_search_read", ({ model }) => {
        expect.step(model);
    });
    await openSearchMoreDialog();
    expect(".modal .o_data_row").toHaveCount(9);
    expect.verifySteps(["hr.employee"]);
});
