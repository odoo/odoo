import { beforeEach, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { mockDate, mockTimeZone } from "@odoo/hoot-mock";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class HrEmployee extends models.ServerModel {
    _name = "hr.employee";

    _records = [{ id: 1, name: "Jane" }];
}

class HrAttendance extends models.Model {
    _name = "hr.attendance";

    check_in = fields.Datetime();
    check_out = fields.Datetime();
    employee_id = fields.Many2one({ relation: "hr.employee" });
    employee_tz = fields.Char();

    _records = [
        // 09:00 -> 17:00 in New York
        { id: 1, check_in: "2026-11-11 14:00:00", check_out: "2026-11-11 22:00:00", employee_id: 1 },
    ];
}

defineModels([HrEmployee, HrAttendance]);
defineMailModels();

const formArch = `
    <form>
        <field name="employee_tz" widget="attendance_tz_warning"/>
        <field name="check_in"/>
        <field name="check_out"/>
        <field name="employee_id"/>
    </form>`;

async function mountAttendance(employeeTz) {
    HrAttendance._records[0].employee_tz = employeeTz;
    await mountView({ type: "form", resModel: "hr.attendance", resId: 1, arch: formArch });
}

beforeEach(() => {
    mockDate("2026-11-06 12:00:00");
});

test("no warning when the browser is in the employee's timezone", async () => {
    mockTimeZone("America/New_York");
    await mountAttendance("America/New_York");
    expect(".o_attendance_tz_warning").toHaveCount(0);
});

test("warning with the employee's hours when the browser is in another timezone", async () => {
    mockTimeZone("Europe/Brussels");
    await mountAttendance("America/New_York");
    expect(".o_attendance_tz_warning").toHaveCount(1);
    const text = queryOne(".o_attendance_tz_warning").textContent;
    expect(text).toInclude("09:00:00");
    expect(text).toInclude("17:00:00");
    expect(text).toInclude("America/New_York");
    expect(text).toInclude("You see the hours in Europe/Brussels.");
});

test("no warning for two timezone names with the same offset", async () => {
    mockTimeZone("Europe/Paris");
    await mountAttendance("Europe/Brussels");
    expect(".o_attendance_tz_warning").toHaveCount(0);
});
