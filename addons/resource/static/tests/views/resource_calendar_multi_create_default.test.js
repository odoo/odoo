import { animationFrame, beforeEach, click, expect, mockDate, test } from "@web/../lib/hoot/hoot";
import { disableAnimations } from "@odoo/hoot-mock";
import { waitFor } from "@odoo/hoot-dom";
import { contains, defineModels, onRpc, webModels } from "@web/../tests/web_test_helpers";
import { mountView } from "@web/../tests/_framework/view_test_helpers";
import { changeScale, clickDate } from "@web/../tests/views/calendar/calendar_test_helpers";
import { ResourceCalendar } from "../mock_server/mock_models/resource_calendar";
import { ResourceCalendarAttendance } from "../mock_server/mock_models/resource_calendar_attendance";

class EightHoursResourceCalendar extends ResourceCalendar {
    _records = [{ id: 1, name: "Variable", calendar_type: "variable", hours_per_day: 7.5 }];

    _views = {
        form: `
            <form>
                <sheet class="mw-100 pb-2 d-flex flex-grow-1">
                    <field name="hours_per_day"/>
                    <field nolabel="1" name="attendance_ids" widget="resource_calendar_attendance_calendar_one2many" class="flex-grow-1"/>
                </sheet>
            </form>
        `,
    };
}

defineModels({ ...webModels, ResourceCalendar: EightHoursResourceCalendar, ResourceCalendarAttendance });

beforeEach(async () => {
    mockDate("2025-01-01 10:00:00");
    disableAnimations();
});

test.tags("desktop");
test(`multi create defaults the duration to the calendar's hours per day`, async () => {
    onRpc("resource.calendar.attendance", "onchange", ({ kwargs, args }) => {
        expect.step(`onchange ${JSON.stringify(args[1])} ${kwargs.context.default_duration_hours}`);
    });
    await mountView({ resId: 1, resModel: "resource.calendar", type: "form" });
    await animationFrame();
    await changeScale("month");
    await animationFrame();
    await clickDate("2025-01-08");
    await animationFrame();
    await click(".o_multi_selection_buttons .btn:contains(Add)");
    await animationFrame();
    await waitFor(".o_multi_create_popover");
    expect.verifySteps(["onchange {} 7.5"]);
    expect(".o_multi_create_popover div[name=duration_hours] input").toHaveValue("7h 30m");
});

test.tags("desktop");
test(`multi create follows a change of the calendar's hours per day`, async () => {
    await mountView({ resId: 1, resModel: "resource.calendar", type: "form" });
    await animationFrame();
    await changeScale("month");
    await animationFrame();
    await clickDate("2025-01-08");
    await animationFrame();
    await click(".o_multi_selection_buttons .btn:contains(Add)");
    await animationFrame();
    await waitFor(".o_multi_create_popover");
    expect(".o_multi_create_popover div[name=duration_hours] input").toHaveValue("7h 30m");
    await click(".o_multi_create_popover .popover-footer .btn:contains(Discard)");
    await animationFrame();
    await contains(".o_form_view div[name=hours_per_day] input").edit("9");
    await animationFrame();
    await click(".o_multi_selection_buttons .btn:contains(Add)");
    await animationFrame();
    await waitFor(".o_multi_create_popover");
    expect(".o_multi_create_popover div[name=duration_hours] input").toHaveValue("9h", {
        message: "the remembered default follows the new hours per day",
    });
    await contains(".o_multi_create_popover div[name=duration_hours] input").edit("4");
    await click(".o_multi_create_popover .popover-footer .btn:contains(Discard)");
    await animationFrame();
    await contains(".o_form_view div[name=hours_per_day] input").edit("8");
    await animationFrame();
    await click(".o_multi_selection_buttons .btn:contains(Add)");
    await animationFrame();
    await waitFor(".o_multi_create_popover");
    expect(".o_multi_create_popover div[name=duration_hours] input").toHaveValue("4h", {
        message: "a duration chosen by the user is kept",
    });
});

test.tags("desktop");
test(`multi create keeps the unsaved changes of the calendar form`, async () => {
    await mountView({ resId: 1, resModel: "resource.calendar", type: "form" });
    await animationFrame();
    await contains(".o_form_view div[name=hours_per_day] input").edit("9");
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
    expect(".o_form_view div[name=hours_per_day] input").toHaveValue("9.00", {
        message: "the unsaved hours per day are not reset by the reload of the calendar",
    });
});
