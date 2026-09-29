import { beforeEach, expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    preloadBundle,
} from "@web/../tests/web_test_helpers";
import { clickEvent, findEvent } from "@web/../tests/views/calendar/calendar_test_helpers";

class HrAttendance extends models.Model {
    _name = "hr.attendance";

    name = fields.Char();
    check_in = fields.Datetime();
    check_out = fields.Datetime();

    _records = [
        {
            id: 1,
            name: "Work - 8h",
            check_in: "2024-01-03 08:00:00",
            check_out: "2024-01-03 16:00:00",
        },
    ];

    _views = {
        form: /* xml */ `
            <form>
                <field name="check_in"/>
                <field name="check_out"/>
                <footer>
                    <button string="Save" special="save" class="btn btn-primary" close="1"/>
                    <button special="cancel" class="btn-secondary" close="1"/>
                    <button string="Delete" name="unlink" type="object" class="btn btn-danger ms-auto"
                        close="1" confirm="Are you sure you want to delete this attendance?"/>
                </footer>
            </form>
        `,
    };
}

defineModels([HrAttendance]);
defineMailModels();
preloadBundle("web.fullcalendar_lib");

const calendarArch = /* xml */ `
    <calendar js_class="attendance_calendar_view"
        date_start="check_in"
        date_stop="check_out"
        mode="week"
        quick_create="0"
        event_open_popup="1"/>
`;

beforeEach(() => {
    mockDate("2024-01-03 10:00:00", 0);
    onRpc("res.users", "read", () => [{ id: 1, employee_id: [1, "Mitchell Admin"] }]);
    onRpc("hr.employee", "search_read", () => []);
});

test("clicking an attendance opens its form dialog instead of the popover", async () => {
    await mountView({ resModel: "hr.attendance", type: "calendar", arch: calendarArch });

    await clickEvent(1);
    await waitFor(".o_dialog .o_form_view");
    expect(".o_cw_popover").toHaveCount(0);
    expect(".o_dialog .modal-title").toHaveText("Open: Work - 8h");
});

test("deleting an attendance from its form dialog removes it from the calendar", async () => {
    onRpc("hr.attendance", "unlink", () => {
        expect.step("unlink");
    });
    await mountView({ resModel: "hr.attendance", type: "calendar", arch: calendarArch });
    expect(findEvent(1)).not.toBe(null);

    await clickEvent(1);
    await contains(".o_dialog footer .btn-danger").click();
    await contains(".o_dialog .modal-footer .btn-primary:contains(Ok)").click();
    expect.verifySteps(["unlink"]);
    expect(".o_dialog").toHaveCount(0);
    expect(findEvent(1)).toBe(null);
});
