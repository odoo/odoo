import { animationFrame, beforeEach, click, expect, mockDate, test } from "@web/../lib/hoot/hoot";
import { disableAnimations } from "@odoo/hoot-mock";
import { waitFor } from "@odoo/hoot-dom";
import { contains, defineModels, onRpc, webModels } from "@web/../tests/web_test_helpers";
import { mountView } from "@web/../tests/_framework/view_test_helpers";
import { changeScale, clickDate } from "@web/../tests/views/calendar/calendar_test_helpers";
import { ResourceCalendar } from "../mock_server/mock_models/resource_calendar";
import { ResourceCalendarAttendance } from "../mock_server/mock_models/resource_calendar_attendance";

class VariableResourceCalendar extends ResourceCalendar {
    _records = [{ id: 1, name: "Variable", calendar_type: "variable", hours_per_week: 38 }];

    _views = {
        form: `
            <form>
                <sheet class="mw-100 pb-2 d-flex flex-grow-1">
                    <field name="hours_per_week" widget="float_time"/>
                    <field nolabel="1" name="attendance_ids" widget="resource_calendar_attendance_calendar_one2many" class="flex-grow-1"/>
                </sheet>
            </form>
        `,
    };
}

defineModels({
    ...webModels,
    ResourceCalendar: VariableResourceCalendar,
    ResourceCalendarAttendance,
});

beforeEach(async () => {
    mockDate("2025-01-01 10:00:00");
    disableAnimations();
});

test.tags("desktop");
test(`multi create keeps the unsaved changes of the calendar form`, async () => {
    onRpc("resource.calendar.attendance", "create", () => {
        expect.step("create");
    });
    await mountView({ resId: 1, resModel: "resource.calendar", type: "form" });
    await animationFrame();
    await contains(".o_form_view div[name=hours_per_week] input").edit("30:24");
    await animationFrame();
    await changeScale("month");
    await animationFrame();
    await clickDate("2025-01-08");
    await animationFrame();
    await click(".o_multi_selection_buttons .btn:contains(Add)");
    await animationFrame();
    await waitFor(".o_multi_create_popover");
    await click(".o_multi_create_popover .popover-footer .btn:contains(Add)");
    await animationFrame();
    expect.verifySteps(["create"]);
    expect(".o_form_view div[name=hours_per_week] input").toHaveValue("30h 24m", {
        message: "the unsaved hours per week are not reset by the reload of the calendar",
    });
});
