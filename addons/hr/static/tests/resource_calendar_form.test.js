import { animationFrame, beforeEach, click, expect, mockDate, test } from "@web/../lib/hoot/hoot";
import { disableAnimations } from "@odoo/hoot-mock";
import { waitFor } from "@odoo/hoot-dom";
import { defineModels, fields, onRpc } from "@web/../tests/web_test_helpers";
import { mountView } from "@web/../tests/_framework/view_test_helpers";
import { defineHrModels } from "@hr/../tests/hr_test_helpers";
import { ResourceCalendar } from "@resource/../tests/mock_server/mock_models/resource_calendar";
import { ResourceCalendarAttendance } from "@resource/../tests/mock_server/mock_models/resource_calendar_attendance";

class SharedResourceCalendar extends ResourceCalendar {
    employees_count = fields.Integer();

    // The schedule is variable and used by more than one employee.
    _records = [{ id: 1, name: "Variable", calendar_type: "variable", employees_count: 3 }];

    _views = {
        form: `
            <form class="o_resource_form">
                <sheet class="mw-100 pb-2 d-flex flex-grow-1">
                    <field name="employees_count" invisible="1"/>
                    <field nolabel="1" name="attendance_ids" widget="resource_calendar_attendance_calendar_one2many" class="flex-grow-1"/>
                </sheet>
            </form>
        `,
    };
}

defineHrModels();
defineModels({ ResourceCalendar: SharedResourceCalendar, ResourceCalendarAttendance });

beforeEach(async () => {
    mockDate("2025-01-01 10:00:00");
    disableAnimations();
});

test.tags("desktop");
test(`a shared variable schedule warns before its attendances are changed`, async () => {
    onRpc("resource.calendar.attendance", "web_save", () => expect.step("web_save"));
    await mountView({
        resId: 1,
        resModel: "resource.calendar",
        type: "form",
    });
    await animationFrame();
    await click(".fc-timegrid-slot-lane[data-time='10:00:00']");
    await animationFrame();
    await waitFor(".o_cw_popover");
    await click(".popover-footer .btn:contains('Save')");
    await animationFrame();
    // Nothing is written as long as the user did not accept to change the schedule of everyone.
    await waitFor(".modal:contains('Confirmation Warning')");
    expect.verifySteps([]);
    await click(".modal-footer .btn:contains('Confirm')");
    await animationFrame();
    expect.verifySteps(["web_save"]);
});
