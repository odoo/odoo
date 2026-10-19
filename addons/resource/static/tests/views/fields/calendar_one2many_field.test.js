import { animationFrame, beforeEach, click, expect, mockDate, test } from "@web/../lib/hoot/hoot";
import { disableAnimations } from "@odoo/hoot-mock";
import { waitFor } from "@odoo/hoot-dom";
import { mountView } from "@web/../tests/_framework/view_test_helpers";
import { defineResourceModels } from "../../resource_test_helpers";

defineResourceModels();
beforeEach(async () => {
    mockDate("2025-01-01 10:00:00");
    disableAnimations();
});

test.tags("desktop");
test(`variable resource calendar visible in the form`, async () => {
    await mountView({
        resId: 1,
        resModel: "resource.calendar",
        type: "form",
    });
    expect(".o_calendar_renderer").toBeDisplayed({
        message: "The calendar should be displayed in the form of a variable resource calendar",
    });
});

test.tags("desktop");
test(`Adding a time window keeps the form buttons enabled`, async () => {
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
    expect(".o_form_button_save").toBeEnabled();
    expect(".o_form_button_cancel").toBeEnabled();
});
