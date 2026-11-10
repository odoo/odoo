import { describe, expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels, fields, models, mountView, onRpc } from "@web/../tests/web_test_helpers";

class HrAttendance extends models.Model {
    _name = "hr.attendance";

    check_in = fields.Datetime();
    check_out = fields.Datetime();
}

describe.current.tags("mobile");

defineModels([HrAttendance]);
defineMailModels();

test("on mobile, the week calendar shows the week number alone", async () => {
    mockDate("2026-10-28 10:00:00");
    onRpc("res.users", "read", () => [{ id: 1, employee_id: false }]);

    await mountView({
        type: "calendar",
        resModel: "hr.attendance",
        arch: `<calendar js_class="attendance_calendar_view" date_start="check_in" date_stop="check_out" mode="week"/>`,
    });

    expect(".o_calendar_header h5").toHaveText(/^Week \d+$/);
});
